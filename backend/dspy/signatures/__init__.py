"""DSPy signatures for sermon analysis."""
# Legacy signatures (will be deprecated)
from backend.dspy.signatures.analyze_context import AnalyzeContext, EXAMPLES as ANALYZE_EXAMPLES
from backend.dspy.signatures.identify_verse_content import IdentifyVerseContent, EXAMPLES as IDENTIFY_EXAMPLES

# New simplified signatures
from backend.dspy.signatures.contains_relevant_verses import ContainsRelevantVerses, EXAMPLES as CONTAINS_EXAMPLES
from backend.dspy.signatures.identify_relevant_verses import IdentifyRelevantVerses, EXAMPLES as IDENTIFY_REL_EXAMPLES

# Ranking signature (used by both old and new)
from backend.dspy.signatures.rank_verses import RankVerses, EXAMPLES as RANK_EXAMPLES

__all__ = [
    # New signatures
    'ContainsRelevantVerses',
    'IdentifyRelevantVerses',
    'RankVerses',
    'CONTAINS_EXAMPLES',
    'IDENTIFY_REL_EXAMPLES',
    'RANK_EXAMPLES',
    # Legacy (deprecated)
    'AnalyzeContext',
    'IdentifyVerseContent',
    'ANALYZE_EXAMPLES',
    'IDENTIFY_EXAMPLES',
]
