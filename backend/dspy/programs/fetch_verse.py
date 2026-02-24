"""FetchRelevantVerse - Simplified 2-step pipeline with temporal awareness.

Major changes from V1:
- Reduced from 3 DSPy modules to 2 (ContainsRelevantVerses + IdentifyRelevantVerses)
- Added temporal context (timestamps, current sermon time, previous verses with times)
- Separated direct reference lookup (SQL) from content-based search (ChromaDB)
- Added anti-hallucination validation for ranking
- Optimized for <2s inference time

Pipeline:
1. ContainsRelevantVerses: Fast yes/no decision + retrieval type
2. IdentifyRelevantVerses: Extract references OR search queries based on type
3. Lookup/Search: SQL for direct refs, ChromaDB for content
4. RankVerses: Select best from candidates (with hallucination protection)
"""
import dspy
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings

from backend.dspy.signatures import (
    ContainsRelevantVerses,
    IdentifyRelevantVerses,
    RankVerses,
    CONTAINS_EXAMPLES,
    IDENTIFY_REL_EXAMPLES,
    RANK_EXAMPLES
)
from backend.utils.config import config
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

# Path to optimized instructions
OPTIMIZED_DIR = Path(__file__).parent.parent.parent.parent / "data" / "optimized_signatures"


def get_signature_hash(signature_class):
    """Generate a hash of the signature's input/output fields.

    This helps detect when the signature definition has changed,
    invalidating cached optimizations.
    """
    import hashlib

    # DSPy signatures use model_fields (Pydantic v2)
    # Collect field definitions
    fields_data = []
    for name, field in signature_class.model_fields.items():
        # Include field name, type, field type (input/output), and prefix
        field_type = field.json_schema_extra.get('__dspy_field_type', 'unknown')
        prefix = field.json_schema_extra.get('prefix', '')
        field_info = f"{name}:{field.annotation}:{field_type}:{prefix}"
        fields_data.append(field_info)

    # Sort for consistency
    fields_data.sort()

    # Create hash
    fields_str = "|".join(fields_data)
    return hashlib.sha256(fields_str.encode()).hexdigest()[:16]


def load_optimized_instructions(signature_name: str, signature_class=None):
    """Load optimized instructions if they exist and signature hasn't changed.

    Args:
        signature_name: Name of the signature
        signature_class: The signature class to validate against

    Returns:
        Optimized instructions string or None if not found/invalid
    """
    import json
    active_file = OPTIMIZED_DIR / f"{signature_name}.json"

    if not active_file.exists():
        return None

    try:
        with open(active_file, 'r') as f:
            data = json.load(f)

        # Validate signature hash if signature class provided
        if signature_class and 'signature_hash' in data:
            current_hash = get_signature_hash(signature_class)
            saved_hash = data['signature_hash']

            if current_hash != saved_hash:
                logger.warning(
                    f"Signature definition has changed for {signature_name}! "
                    f"Saved hash: {saved_hash}, Current hash: {current_hash}. "
                    f"Ignoring cached optimization - please re-run optimization."
                )
                return None

        logger.info(f"Loaded GEPA-optimized instructions for {signature_name} (candidate {data.get('best_candidate_idx', 'unknown')})")
        return data['instructions'].get('predict')
    except Exception as e:
        logger.warning(f"Failed to load optimized instructions for {signature_name}: {e}")
        return None


class FetchRelevantVerse(dspy.Module):
    """Simplified verse retrieval pipeline with temporal awareness and queue support.

    Complete pipeline:
    1. ContainsRelevantVerses: Quick filter (skip admin/vague content)
    2. IdentifyRelevantVerses: Extract refs OR queries based on type
    3. Search: SQL lookup (direct) OR ChromaDB (content-based)
    4. RankVerses: Select best candidate (with anti-hallucination)

    Designed for queue-based processing:
    - Fast inference (<2s target)
    - Returns candidates for queue voting mechanism
    - Temporal context for better LLM decisions
    """

    # Class-level shared resources
    _shared_embedding_model = None
    _shared_db_path = None

    def __init__(self, lm: Optional[dspy.LM] = None, embedding_model=None):
        super().__init__()

        # Configure LM
        if lm is None:
            lm = dspy.LM(model="gemini/gemini-2.5-flash", api_key=config.GEMINI_API_KEY)
        self.lm = lm

        # Initialize DSPy modules
        logger.info("Initializing ContainsRelevantVerses module with %d examples", len(CONTAINS_EXAMPLES))
        self.contains = dspy.ChainOfThought(ContainsRelevantVerses, lm=self.lm)
        self.contains.demos = CONTAINS_EXAMPLES

        logger.info("Initializing IdentifyRelevantVerses module with %d examples", len(IDENTIFY_REL_EXAMPLES))
        self.identify = dspy.ChainOfThought(IdentifyRelevantVerses, lm=self.lm)
        self.identify.demos = IDENTIFY_REL_EXAMPLES

        logger.info("Initializing RankVerses module with %d examples", len(RANK_EXAMPLES))
        optimized_rank = load_optimized_instructions("rank_verses", RankVerses)
        if optimized_rank:
            rank_sig = RankVerses.with_instructions(optimized_rank)
            self.rank = dspy.ChainOfThought(rank_sig, lm=self.lm)
        else:
            self.rank = dspy.ChainOfThought(RankVerses, lm=self.lm)
        self.rank.demos = RANK_EXAMPLES

        # Initialize embedding model (shared across instances)
        if embedding_model is not None:
            self.embedding_model = embedding_model
        else:
            if FetchRelevantVerse._shared_embedding_model is None:
                FetchRelevantVerse._shared_embedding_model = SentenceTransformer('all-mpnet-base-v2')
                logger.info("Loaded shared embedding model: all-mpnet-base-v2 (768 dims)")
            else:
                logger.info("Using shared embedding model: all-mpnet-base-v2 (768 dims)")
            self.embedding_model = FetchRelevantVerse._shared_embedding_model

        # Initialize ChromaDB
        self._setup_chromadb()

        # Initialize SQLite connection
        self._setup_sqlite()

        # Configuration
        self.top_k = config.get('verse_retrieval.top_k_candidates', 5)
        self.min_relevance = config.get('verse_retrieval.min_relevance_score', 75)

        logger.info(f"FetchRelevantVerse initialized (top_k: {self.top_k}, min_relevance: {self.min_relevance})")

    def _setup_chromadb(self):
        """Set up ChromaDB client and collection."""
        db_path = Path(__file__).parent.parent.parent.parent / "data" / "chromadb"
        db_path.mkdir(parents=True, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=str(db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        collection_name = "bible_verses"
        try:
            self.collection = self.client.get_collection(name=collection_name)
            logger.info(f"Connected to ChromaDB collection: {collection_name}")
        except Exception:
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata={"description": "Bible verses for sermon display"}
            )
            logger.info(f"Created ChromaDB collection: {collection_name}")

    def _setup_sqlite(self):
        """Set up SQLite database connection."""
        if FetchRelevantVerse._shared_db_path is None:
            FetchRelevantVerse._shared_db_path = Path(__file__).parent.parent.parent.parent / "data" / "verses.sqlite"
        self.db_path = FetchRelevantVerse._shared_db_path
        logger.info(f"Using SQLite database: {self.db_path}")

    def forward(
        self,
        current_time: str,
        context: str,
        previous_verses: str,
        queued_verses: str = "",
        excluded_references: List[str] = None
    ) -> Optional[Dict]:
        """
        Retrieve most relevant verse for sermon context.

        Args:
            current_time: Current sermon position as MM:SS (e.g., "15:23")
            context: Timestamped transcript with [MM:SS] prefixes
            previous_verses: Previously shown verses with format "[MM:SS] Reference"
            queued_verses: Verses currently in queue as 'Reference' per line (prevents re-detection)
            excluded_references: Additional refs to exclude

        Returns:
            Dict with verse data or None:
            {
                'verse_reference': str,
                'verse_text': str,
                'relevance_score': int,
                'why_relevant': str,
                'theme': str
            }
        """
        import time
        start_time = time.time()
        excluded_references = excluded_references or []

        try:
            # Step 1: Check if context contains retrievable biblical content
            step1_start = time.time()
            logger.info("Step 1: Checking for biblical content...")

            contains_result = self.contains(
                current_time=current_time,
                context=context,
                previous_verses=previous_verses,
                queued_verses=queued_verses
            )
            step1_time = time.time() - step1_start

            if not contains_result.contains_verses:
                logger.info(f"No retrievable biblical content (Step 1: {step1_time:.2f}s) - Reason: {contains_result.reasoning}")
                return {
                    'skipped': True,
                    'reasoning': contains_result.reasoning,
                    'retrieval_type': contains_result.retrieval_type
                }

            logger.info(f"Retrieval type: {contains_result.retrieval_type} (Step 1: {step1_time:.2f}s)")
            logger.info(f"Reasoning: {contains_result.reasoning}")

            # Step 2: Extract verse references or search queries
            step2_start = time.time()
            logger.info("Step 2: Extracting verse info...")

            identify_result = self.identify(
                current_time=current_time,
                context=context,
                previous_verses=previous_verses,
                queued_verses=queued_verses
            )
            step2_time = time.time() - step2_start

            # Step 3: Search for candidates (combine both direct and content-based)
            step3_start = time.time()
            candidates = []

            # Try direct references first if provided
            if identify_result.verse_references and identify_result.verse_references.strip():
                logger.info(f"Step 3a: Looking up direct references: {identify_result.verse_references}")
                direct_candidates = self._lookup_direct_references(
                    identify_result.verse_references,
                    excluded_references
                )
                candidates.extend(direct_candidates)

            # Add content-based search if queries provided
            if identify_result.search_queries and identify_result.search_queries.strip():
                logger.info(f"Step 3b: Searching by content...")
                logger.info(f"Search queries: {identify_result.search_queries[:100]}...")
                if identify_result.biblical_entities:
                    logger.info(f"Biblical entities: {identify_result.biblical_entities}")
                content_candidates = self._search_by_content(
                    context=context,
                    search_queries=identify_result.search_queries,
                    biblical_entities=identify_result.biblical_entities,
                    excluded_references=excluded_references
                )
                # Merge candidates, avoiding duplicates
                existing_refs = {c['reference'].lower() for c in candidates}
                for candidate in content_candidates:
                    if candidate['reference'].lower() not in existing_refs:
                        candidates.append(candidate)
                        existing_refs.add(candidate['reference'].lower())

            step3_time = time.time() - step3_start

            if not candidates:
                logger.warning(f"No verse candidates found (Step 3: {step3_time:.2f}s)")
                return None

            logger.info(f"Found {len(candidates)} candidates (Step 3: {step3_time:.2f}s)")

            # Derive simple theme for queue metadata (first search query or reasoning summary)
            if identify_result.search_queries and identify_result.search_queries.strip():
                theme = identify_result.search_queries.split(';')[0].strip()[:50]
            else:
                theme = contains_result.reasoning[:50] if contains_result.reasoning else "biblical relevance"

            # Return top 3 RRF-ranked candidates for enqueueing (ranking happens later at display time)
            top_candidates = []
            for candidate in candidates[:3]:  # Top 3 from RRF ranking
                top_candidates.append({
                    'verse_reference': candidate['reference'],
                    'verse_text': candidate['text'],
                    'relevance_score': candidate.get('score', 100),
                    'theme': theme
                })

            total_time = time.time() - start_time
            logger.info(
                f"✓ Retrieved {len(top_candidates)} candidates for queue "
                f"[Step 1: {step1_time:.2f}s, Step 2: {step2_time:.2f}s, Step 3: {step3_time:.2f}s, Total: {total_time:.2f}s]"
            )

            return {
                'candidates': top_candidates,
                'contains_reasoning': contains_result.reasoning  # For status bar
            }

        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"Verse retrieval failed: {e} (Total: {total_time:.2f}s)", exc_info=True)
            return None

    def _lookup_direct_references(self, references_str: str, excluded: List[str]) -> List[Dict]:
        """Look up verse references using ChromaDB metadata filtering.

        Uses direct metadata search for exact reference matching - much faster
        than semantic search since it doesn't require embedding generation.

        Args:
            references_str: Semicolon-separated references (e.g., "Matthew 6:27; Psalm 23:1")
            excluded: References to exclude

        Returns:
            List of candidates with reference and text
        """
        if not references_str or not references_str.strip():
            return []

        refs = [r.strip() for r in references_str.split(';') if r.strip()]
        candidates = []
        excluded_lower = [e.lower() for e in excluded]

        for ref in refs:
            if ref.lower() in excluded_lower:
                logger.debug(f"Skipping excluded reference: {ref}")
                continue

            try:
                # Direct metadata search using reference_lower
                results = self.collection.get(
                    where={"reference_lower": {"$eq": ref.lower()}},
                    include=['metadatas']
                )

                if results['ids'] and len(results['ids']) > 0:
                    metadata = results['metadatas'][0]
                    candidates.append({
                        'reference': metadata.get('reference'),
                        'text': metadata.get('text'),
                        'score': 100
                    })
                    logger.debug(f"Found verse via ChromaDB metadata: {metadata.get('reference')}")
                else:
                    logger.warning(f"Verse not found in ChromaDB: {ref}")

            except Exception as e:
                logger.error(f"ChromaDB metadata query failed for '{ref}': {e}")

        return candidates[:self.top_k]

    def _search_by_content(
        self,
        context: str,
        search_queries: str,
        biblical_entities: str,
        excluded_references: List[str]
    ) -> List[Dict]:
        """Search ChromaDB using semantic similarity (RRF multi-query).

        Args:
            context: Raw sermon transcript
            search_queries: Semicolon-separated search queries
            biblical_entities: Comma-separated entity names
            excluded_references: Verses to exclude

        Returns:
            Top-k verses ranked by RRF score
        """
        RRF_K = 60  # Standard RRF constant
        rrf_scores = {}
        verse_data = {}

        # Collect all queries
        all_queries = []

        # Add raw context as first query (most important)
        all_queries.append(context)

        # Add search queries
        if search_queries:
            queries = [q.strip() for q in search_queries.split(';') if q.strip()]
            all_queries.extend(queries[:3])  # Limit to 3

        # Add entities
        if biblical_entities:
            entities = [e.strip() for e in biblical_entities.split(',') if e.strip()]
            all_queries.extend(entities[:5])  # Limit to 5

        # Execute each query and accumulate RRF scores
        for query in all_queries:
            query_embedding = self._generate_embedding(query)
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=self.top_k * 2,
                include=['metadatas', 'distances', 'documents']
            )

            if results['ids'] and len(results['ids'][0]) > 0:
                for rank, i in enumerate(range(len(results['ids'][0]))):
                    metadata = results['metadatas'][0][i]
                    reference = metadata.get('reference')

                    if reference not in excluded_references:
                        # RRF scoring: 1 / (k + rank)
                        rrf_contribution = 1.0 / (RRF_K + rank)

                        if reference in rrf_scores:
                            rrf_scores[reference] += rrf_contribution
                        else:
                            rrf_scores[reference] = rrf_contribution
                            verse_data[reference] = {
                                'reference': reference,
                                'text': metadata.get('text')
                            }

        if not rrf_scores:
            return []

        # Convert to candidate format
        candidates = []
        for reference, rrf_score in rrf_scores.items():
            candidates.append({
                'reference': reference,
                'text': verse_data[reference]['text'],
                'score': rrf_score
            })

        # Sort by RRF score and return top_k
        sorted_candidates = sorted(candidates, key=lambda x: x['score'], reverse=True)
        return sorted_candidates[:self.top_k]

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding vector for text."""
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
