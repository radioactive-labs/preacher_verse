"""VerseQueue - manages queue of candidate verses with voting and aging mechanism."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class QueuedVerse:
    """A verse candidate in the queue with temporal tracking.

    Voting mechanism: Same verse selected multiple times = higher confidence
    Aging mechanism: Items not selected for 3 cycles get dropped
    """

    reference: str
    text: str
    theme: str
    initial_score: int

    # Voting and aging
    selection_count: int = 1  # How many 10s windows selected this
    age: int = 0  # Turns since last selected (0-2, then dropped)

    # Temporal tracking
    first_detected_at: datetime = field(default_factory=datetime.now)
    last_selected_at: datetime = field(default_factory=datetime.now)
    sermon_timestamps: List[str] = field(default_factory=list)  # ["15:23", "15:33"]

    def time_in_queue(self) -> float:
        """How long has this been in queue (seconds)?"""
        return (datetime.now() - self.first_detected_at).total_seconds()

    def voting_score(self) -> float:
        """Calculate score based on selection count and recency.

        Higher selection_count + lower age = higher score
        """
        recency_bonus = (3 - self.age) * 10  # 30, 20, 10, 0
        return self.initial_score + (self.selection_count * 15) + recency_bonus


class VerseQueue:
    """Queue manager for verse candidates with voting and aging.

    Flow:
    1. Detection thread adds candidates every 10s (same verse multiple times = votes)
    2. Display thread (every 15s) re-ranks queue and displays winner
    3. After display, age all items (increment age, drop old ones)

    Queue size: Max 3 items
    Aging rule: Items with age >= 3 get dropped (not selected for 3 cycles)
    """

    def __init__(self, max_size: int = 3):
        self.max_size = max_size
        self.queue: List[QueuedVerse] = []

    def add_candidate(self, verse_ref: str, verse_text: str, score: int, theme: str, sermon_time: str):
        """Add verse candidate to queue or increment selection count if already present."""
        # Check if verse already in queue
        for item in self.queue:
            if item.reference.lower() == verse_ref.lower():
                # Already in queue - increment selection count and reset age
                item.selection_count += 1
                item.age = 0  # Reset age since it was selected again
                item.last_selected_at = datetime.now()
                if sermon_time not in item.sermon_timestamps:
                    item.sermon_timestamps.append(sermon_time)
                logger.info(
                    f"Verse {verse_ref} re-selected in queue "
                    f"(count: {item.selection_count}, age: {item.age}, voting_score: {item.voting_score():.1f})"
                )
                return

        # New verse - add to queue
        new_item = QueuedVerse(
            reference=verse_ref,
            text=verse_text,
            theme=theme,
            initial_score=score,
            selection_count=1,
            age=0,
            sermon_timestamps=[sermon_time]
        )

        self.queue.append(new_item)
        logger.info(f"Added new verse to queue: {verse_ref} (score: {score}, voting_score: {new_item.voting_score():.1f})")

    def age_items(self):
        """Increment age for all items, drop items with age >= 3."""
        for item in self.queue:
            item.age += 1

        # Remove aged-out items
        before_count = len(self.queue)
        self.queue = [item for item in self.queue if item.age < 3]
        removed_count = before_count - len(self.queue)

        if removed_count > 0:
            logger.info(f"Aged out {removed_count} verse(s) from queue (age >= 3)")

    def get_candidates_for_ranking(self) -> List[Dict]:
        """Return queue items formatted for RankVerses signature.

        Returns list sorted by voting_score (highest first).
        """
        if not self.queue:
            return []

        # Sort by voting score
        sorted_queue = sorted(self.queue, key=lambda x: x.voting_score(), reverse=True)

        candidates = []
        for item in sorted_queue:
            candidates.append({
                'reference': item.reference,
                'text': item.text,
                'theme': item.theme,
                'score': item.initial_score,
                'selection_count': item.selection_count,
                'age': item.age,
                'voting_score': item.voting_score(),
                'sermon_timestamps': item.sermon_timestamps
            })

        return candidates

    def remove_verse(self, verse_ref: str):
        """Remove verse from queue after display."""
        before_count = len(self.queue)
        self.queue = [item for item in self.queue if item.reference.lower() != verse_ref.lower()]

        if len(self.queue) < before_count:
            logger.info(f"Removed displayed verse from queue: {verse_ref}")

    def get_queue_status(self) -> str:
        """Get human-readable queue status for logging."""
        if not self.queue:
            return "Queue empty"

        sorted_queue = sorted(self.queue, key=lambda x: x.voting_score(), reverse=True)
        items = []
        for item in sorted_queue:
            items.append(
                f"{item.reference} (count:{item.selection_count}, age:{item.age}, score:{item.voting_score():.0f})"
            )
        return f"Queue ({len(self.queue)}): " + ", ".join(items)

    def clear(self):
        """Clear entire queue."""
        self.queue.clear()
        logger.info("Queue cleared")

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self.queue) == 0

    def size(self) -> int:
        """Get current queue size."""
        return len(self.queue)
