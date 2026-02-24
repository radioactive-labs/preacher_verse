"""VerseDisplayEvent - captures all data about a verse display for logging and analytics."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class VerseDisplayEvent:
    """Complete record of a verse display event with temporal and contextual data.

    This enables:
    - Post-sermon replay with exact timing
    - Correlation analysis between sermon flow and verse selection
    - Training data generation from real sermons
    - Analytics on verse selection patterns
    """

    # Verse data
    verse_reference: str
    verse_text: str
    theme: str
    relevance_score: int
    why_relevant: str  # LLM reasoning

    # Timing data
    displayed_at: datetime  # Absolute timestamp when broadcast to frontend
    sermon_timestamp: str  # Relative position in sermon (MM:SS format)

    # Context preservation
    sermon_context: str  # The 60s transcript window that triggered this
    transcript_start: str  # Start time of context window (MM:SS)
    transcript_end: str  # End time of context window (MM:SS)

    # Metadata
    session_id: str  # Sermon session identifier
    selection_count: Optional[int] = None  # How many times selected in queue (if using queue)
    queue_age: Optional[int] = None  # How long it waited in queue (if using queue)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'verse_reference': self.verse_reference,
            'verse_text': self.verse_text,
            'theme': self.theme,
            'relevance_score': self.relevance_score,
            'why_relevant': self.why_relevant,
            'displayed_at': self.displayed_at.isoformat() if isinstance(self.displayed_at, datetime) else self.displayed_at,
            'sermon_timestamp': self.sermon_timestamp,
            'sermon_context': self.sermon_context,
            'transcript_start': self.transcript_start,
            'transcript_end': self.transcript_end,
            'session_id': self.session_id,
            'selection_count': self.selection_count,
            'queue_age': self.queue_age,
        }

    def to_frontend_data(self) -> dict:
        """Convert to format expected by frontend."""
        return {
            'reference': self.verse_reference,
            'text': self.verse_text,
            'theme': self.theme,
            'relevance_score': self.relevance_score,
            'why_relevant': self.why_relevant,
            'sermon_time': self.sermon_timestamp,
            'displayed_at': self.displayed_at.isoformat() if isinstance(self.displayed_at, datetime) else self.displayed_at,
            'transcript_range': {
                'start': self.transcript_start,
                'end': self.transcript_end
            }
        }
