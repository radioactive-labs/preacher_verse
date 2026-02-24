#!/usr/bin/env python3
"""Populate ChromaDB with Bible verses from KJV JSON files."""

import sys
import json
from pathlib import Path
from typing import List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models.database import get_session, Verse, init_db
from backend.dspy import FetchRelevantVerse
from backend.services.verse_enricher import VerseEnricher
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

def load_kjv_bible(bible_dir: Path) -> List[Tuple[str, str, List[str]]]:
    """
    Load all Bible verses from KJV JSON files.

    Returns:
        List of tuples: (reference, text, tags)
    """
    books_file = bible_dir / "Books.json"
    if not books_file.exists():
        raise FileNotFoundError(f"Books.json not found in {bible_dir}")

    with open(books_file) as f:
        books = json.load(f)

    all_verses = []
    total_books = len(books)

    for idx, book_name in enumerate(books, 1):
        # Convert book name to filename (e.g., "1 Samuel" -> "1Samuel.json")
        filename = book_name.replace(" ", "") + ".json"
        book_file = bible_dir / filename

        if not book_file.exists():
            logger.warning(f"File not found: {book_file}")
            continue

        logger.info(f"Loading {book_name} ({idx}/{total_books})...")

        with open(book_file) as f:
            book_data = json.load(f)

        for chapter in book_data.get("chapters", []):
            chapter_num = chapter["chapter"]

            for verse in chapter.get("verses", []):
                verse_num = verse["verse"]
                text = verse["text"]

                # Create reference
                reference = f"{book_name} {chapter_num}:{verse_num}"

                # Auto-tag based on book category (basic tagging)
                tags = get_auto_tags(book_name)

                all_verses.append((reference, text, tags))

    return all_verses


def get_auto_tags(book_name: str) -> List[str]:
    """Generate basic tags based on book category."""
    # Old Testament
    law_books = ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy"]
    history_books = ["Joshua", "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings",
                     "2 Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther"]
    wisdom_books = ["Job", "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon"]
    major_prophets = ["Isaiah", "Jeremiah", "Lamentations", "Ezekiel", "Daniel"]
    minor_prophets = ["Hosea", "Joel", "Amos", "Obadiah", "Jonah", "Micah", "Nahum",
                      "Habakkuk", "Zephaniah", "Haggai", "Zechariah", "Malachi"]

    # New Testament
    gospels = ["Matthew", "Mark", "Luke", "John"]
    pauline_epistles = ["Romans", "1 Corinthians", "2 Corinthians", "Galatians",
                        "Ephesians", "Philippians", "Colossians", "1 Thessalonians",
                        "2 Thessalonians", "1 Timothy", "2 Timothy", "Titus", "Philemon"]
    general_epistles = ["Hebrews", "James", "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude"]

    tags = []

    if book_name in law_books:
        tags = ["old_testament", "law", "torah"]
    elif book_name in history_books:
        tags = ["old_testament", "history"]
    elif book_name in wisdom_books:
        tags = ["old_testament", "wisdom", "poetry"]
    elif book_name in major_prophets:
        tags = ["old_testament", "prophecy", "major_prophet"]
    elif book_name in minor_prophets:
        tags = ["old_testament", "prophecy", "minor_prophet"]
    elif book_name in gospels:
        tags = ["new_testament", "gospel", "jesus"]
    elif book_name == "Acts":
        tags = ["new_testament", "history", "early_church"]
    elif book_name in pauline_epistles:
        tags = ["new_testament", "epistle", "paul"]
    elif book_name in general_epistles:
        tags = ["new_testament", "epistle"]
    elif book_name == "Revelation":
        tags = ["new_testament", "prophecy", "apocalyptic"]

    return tags


def parse_reference(ref: str):
    """Parse a verse reference into book, chapter, verse."""
    parts = ref.split()

    # Handle multi-word books (look for the part with chapter:verse)
    # Find the location part (contains ':')
    location_idx = None
    for i, part in enumerate(parts):
        if ':' in part:
            location_idx = i
            break

    if location_idx is None:
        raise ValueError(f"No chapter:verse found in reference: {ref}")

    # Everything before location_idx is the book name
    book = ' '.join(parts[:location_idx])
    location = parts[location_idx]

    chapter, verse = location.split(':')

    # Handle verse ranges (take first verse)
    if '-' in verse:
        verse = verse.split('-')[0]

    return book, int(chapter), int(verse)

def main():
    """Populate database and ChromaDB with verses."""
    import argparse

    parser = argparse.ArgumentParser(description="Populate Bible verses database")
    parser.add_argument(
        "--bible-dir",
        type=Path,
        default=Path(__file__).parent.parent / "data" / "bible-kjv",
        help="Directory containing KJV JSON files"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Number of verses to commit per batch (for large imports)"
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        default=True,
        help="Enable contextual enrichment using Qwen 2.5 1.5B (slower but better search quality)"
    )
    parser.add_argument(
        "--force-enrich",
        action="store_true",
        help="Force re-enrichment of all verses, even if already enriched (requires --enrich)"
    )

    args = parser.parse_args()

    logger.info(f"Populating verses from KJV Bible...")

    try:
        # Initialize database tables
        logger.info("Initializing database...")
        init_db()

        # Initialize services
        session = get_session()
        fetch_verse = FetchRelevantVerse()

        # Initialize enricher if requested
        enricher = None
        if args.enrich:
            logger.info("Initializing verse enricher (Qwen 2.5 1.5B)...")
            enricher = VerseEnricher()
            logger.info("Enricher ready")

        # Load verses from KJV Bible
        logger.info(f"Loading full KJV Bible from {args.bible_dir}...")
        verses = load_kjv_bible(args.bible_dir)
        logger.info(f"Loaded {len(verses)} verses from KJV Bible")

        # Process verses in batches
        total_verses = len(verses)
        batch_size = args.batch_size
        added_count = 0
        updated_count = 0

        for i in range(0, total_verses, batch_size):
            batch = verses[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_verses + batch_size - 1) // batch_size

            logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} verses)...")

            # Pre-load all existing verses in this batch (single query)
            batch_refs = [ref for ref, _, _ in batch]
            existing_verses = session.query(Verse).filter(Verse.reference.in_(batch_refs)).all()
            existing_map = {v.reference: v for v in existing_verses}
            logger.debug(f"Pre-loaded {len(existing_verses)} existing verses from batch")

            # Process verses one at a time (with immediate saves)
            batch_enrichments = []
            for idx, (reference, text, tags) in enumerate(batch):
                verse_num = i + idx + 1  # Global verse number

                # Parse reference
                try:
                    book, chapter, verse = parse_reference(reference)
                except Exception as e:
                    logger.error(f"Failed to parse reference '{reference}': {e}")
                    logger.error(f"  Text: {text[:100]}...")
                    raise

                # Get existing verse from pre-loaded map
                existing = existing_map.get(reference)

                # Generate enrichment if enabled and not already enriched
                enriched = ''
                if enricher:
                    # Skip if already enriched (unless --force-enrich)
                    if existing and existing.enriched_text and not args.force_enrich:
                        enriched = existing.enriched_text
                        logger.info(f"  [{verse_num}/{total_verses}] {reference} - Using cached enrichment")
                    else:
                        logger.info(f"  [{verse_num}/{total_verses}] {reference} - Enriching...")
                        try:
                            enriched = enricher.enrich_verse(reference, text)
                            logger.info(f"  [{verse_num}/{total_verses}] {reference} - ✓ Enriched")
                        except Exception as e:
                            logger.warning(f"  [{verse_num}/{total_verses}] {reference} - ✗ Failed: {e}")
                else:
                    logger.info(f"  [{verse_num}/{total_verses}] {reference}")

                batch_enrichments.append(enriched)

                # Add/update to SQLite and commit immediately (no data loss on failure)
                if not existing:
                    db_verse = Verse(
                        book=book,
                        chapter=chapter,
                        verse=verse,
                        reference=reference,
                        text=text,
                        enriched_text=enriched,
                        manual_tags=','.join(tags)
                    )
                    session.add(db_verse)
                    added_count += 1
                else:
                    existing.text = text
                    existing.enriched_text = enriched
                    existing.manual_tags = ','.join(tags)
                    updated_count += 1

                # Commit after each verse to ensure no data loss
                session.commit()

            logger.info(f"  SQLite: Committed {len(batch)} verses")

            # Add to ChromaDB in batch (embeddings are still batched for speed)
            fetch_verse.upsert_verses_batch(batch, enrichments=batch_enrichments if enricher else None)
            logger.info(f"  ChromaDB: Added {len(batch)} verses with embeddings")

        # Show stats
        total_db_verses = session.query(Verse).count()
        chroma_stats = fetch_verse.get_collection_stats()

        logger.info(f"\n{'='*60}")
        logger.info(f"✓ Population completed successfully!")
        logger.info(f"  Added: {added_count} verses")
        logger.info(f"  Updated: {updated_count} verses")
        logger.info(f"  SQLite total: {total_db_verses} verses")
        logger.info(f"  ChromaDB: {chroma_stats}")
        logger.info(f"{'='*60}")

        session.close()

    except Exception as e:
        logger.error(f"Failed to populate verses: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
