"""DSPy signatures for sermon analysis."""

from backend.dspy.signatures.contains_relevant_verses import ContainsRelevantVerses, EXAMPLES as CONTAINS_EXAMPLES
from backend.dspy.signatures.identify_relevant_verses import IdentifyRelevantVerses, EXAMPLES as IDENTIFY_REL_EXAMPLES
from backend.dspy.signatures.rank_verses import RankVerses, EXAMPLES as RANK_EXAMPLES

__all__ = [
    'ContainsRelevantVerses',
    'IdentifyRelevantVerses',
    'RankVerses',
    'CONTAINS_EXAMPLES',
    'IDENTIFY_REL_EXAMPLES',
    'RANK_EXAMPLES',
]
