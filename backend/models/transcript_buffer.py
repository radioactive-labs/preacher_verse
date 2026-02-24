from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List
from backend.utils.logger import setup_logger
from backend.utils.config import config

logger = setup_logger(__name__)

@dataclass
class TranscriptSegment:
    """A segment of transcribed text with timestamp."""
    text: str
    timestamp: datetime

    def get_sermon_time(self, sermon_start: datetime) -> str:
        """Get this segment's position in sermon as MM:SS."""
        if not sermon_start:
            return "00:00"
        elapsed = (self.timestamp - sermon_start).total_seconds()
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        return f"{mins:02d}:{secs:02d}"

class TranscriptBuffer:
    """
    Maintains rolling windows of transcribed text.

    - Active window: Most recent N seconds of speech for theme extraction
    - Context window: Historical context to understand theme development
    """

    def __init__(
        self,
        context_window_seconds: int = None,
        active_window_seconds: int = None
    ):
        self.context_window_seconds = context_window_seconds or config.CONTEXT_WINDOW_SECONDS
        self.active_window_seconds = active_window_seconds or config.ACTIVE_WINDOW_SECONDS
        self.segments: List[TranscriptSegment] = []

        logger.info(
            f"TranscriptBuffer initialized: "
            f"context={self.context_window_seconds}s, "
            f"active={self.active_window_seconds}s"
        )

    def add_segment(self, text: str, timestamp: datetime = None):
        """Add a new transcript segment."""
        if not text or not text.strip():
            return

        timestamp = timestamp or datetime.now()
        segment = TranscriptSegment(text=text.strip(), timestamp=timestamp)
        self.segments.append(segment)

        logger.debug(f"Added segment: {text[:50]}... at {timestamp}")

        # Cleanup old segments
        self._cleanup()

    def get_active_window(self) -> str:
        """Get the most recent active window of text."""
        cutoff = datetime.now() - timedelta(seconds=self.active_window_seconds)
        active_segments = [
            seg for seg in self.segments
            if seg.timestamp >= cutoff
        ]

        text = " ".join(seg.text for seg in active_segments)
        logger.debug(f"Active window ({len(active_segments)} segments): {text[:100]}...")
        return text

    def get_context_window(self) -> str:
        """Get the full context window of text."""
        cutoff = datetime.now() - timedelta(seconds=self.context_window_seconds)
        context_segments = [
            seg for seg in self.segments
            if seg.timestamp >= cutoff
        ]

        text = " ".join(seg.text for seg in context_segments)
        logger.debug(f"Context window ({len(context_segments)} segments): {text[:100]}...")
        return text

    def get_word_count(self) -> int:
        """Get word count in active window."""
        active_text = self.get_active_window()
        return len(active_text.split())

    def _cleanup(self):
        """Remove segments older than context window."""
        cutoff = datetime.now() - timedelta(seconds=self.context_window_seconds)
        before_count = len(self.segments)

        self.segments = [
            seg for seg in self.segments
            if seg.timestamp >= cutoff
        ]

        removed = before_count - len(self.segments)
        if removed > 0:
            logger.debug(f"Cleaned up {removed} old segments")

    def get_context_segments(self) -> List[TranscriptSegment]:
        """Get list of transcript segments in context window."""
        cutoff = datetime.now() - timedelta(seconds=self.context_window_seconds)
        context_segments = [
            seg for seg in self.segments
            if seg.timestamp >= cutoff
        ]
        return context_segments

    def get_timestamped_context(self, sermon_start: datetime = None) -> str:
        """Get context window formatted with [MM:SS] timestamps for LLM input."""
        segments = self.get_context_segments()
        if not segments:
            return ""

        formatted_lines = []
        for seg in segments:
            sermon_time = seg.get_sermon_time(sermon_start) if sermon_start else "00:00"
            formatted_lines.append(f"[{sermon_time}] {seg.text}")

        return "\n".join(formatted_lines)

    def get_sermon_timestamp(self, sermon_start: datetime = None) -> str:
        """Get current position in sermon as MM:SS."""
        if not sermon_start:
            return "00:00"
        elapsed = (datetime.now() - sermon_start).total_seconds()
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        return f"{mins:02d}:{secs:02d}"

    def get_time_range(self, sermon_start: datetime = None) -> tuple[str, str]:
        """Get (start_time, end_time) of current context window as MM:SS."""
        segments = self.get_context_segments()
        if not segments:
            return ("00:00", "00:00")

        start_time = segments[0].get_sermon_time(sermon_start) if sermon_start else "00:00"
        end_time = segments[-1].get_sermon_time(sermon_start) if sermon_start else "00:00"
        return (start_time, end_time)

    def clear(self):
        """Clear all segments."""
        self.segments.clear()
        logger.info("TranscriptBuffer cleared")
