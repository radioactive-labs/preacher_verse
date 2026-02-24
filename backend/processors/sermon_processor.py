"""SermonProcessor - Queue-based verse detection with display worker thread.

Features:
- Separates detection (every 10s) from display (1s polling, 20s cooldown)
- VerseQueue with voting mechanism
- Uses FetchRelevantVerse (2-step simplified pipeline)
- Tracks temporal context (sermon timestamps)
- Logs all verse display events for analytics
- Display worker runs in background, re-ranks queue before displaying
- Per-room cooldown tracking (no global dependencies)
- Independent aging and display cooldowns
"""
import asyncio
from datetime import datetime
from typing import List, Optional

from backend.models.transcript_buffer import TranscriptBuffer
from backend.models.verse_queue import VerseQueue
from backend.models.verse_display_event import VerseDisplayEvent
from backend.dspy import FetchRelevantVerse
from backend.dspy.signatures.rank_verses import RankVerses
from backend.services.websocket_server import WebSocketServer
from backend.utils.logger import setup_logger
from backend.utils.config import config
import dspy

logger = setup_logger(__name__)


class SermonProcessor:
    """
    Queue-based sermon processor with separated detection and display.

    Architecture:
    1. Detection thread (every 10s): Fast analysis → add to queue
    2. Display thread (every 1s): Check queue → display when ready
    3. Queue: Max 3 items, voting mechanism, aging

    Flow:
    - Transcript → Detection (FetchRelevantVerse) → Queue
    - Queue → Display Worker → Broadcast → Log
    """

    def __init__(self, websocket_server: WebSocketServer, lm=None):
        self.transcript_buffer = TranscriptBuffer()
        self.ws_server = websocket_server

        # Temporal tracking
        self.sermon_start_time: Optional[datetime] = None
        self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Queue and logging
        self.verse_queue = VerseQueue(max_size=3)
        self.verse_display_log: List[VerseDisplayEvent] = []
        self.recent_verses: List[str] = []  # Track recently shown verses (for duplicate prevention)
        self.recent_verses_limit = 10  # Keep last N verses

        # Timing controls (from config)
        self.last_detection_time = None
        self.detection_interval_seconds = config.ACTIVE_WINDOW_SECONDS  # How often to run verse detection
        self.display_cooldown_seconds = config.COOLDOWN_SECONDS  # Min time between displayed verses
        self.last_verse_displayed_at: Optional[datetime] = None  # Track cooldown per-room
        self.last_queue_aged_at: Optional[datetime] = None  # Track aging schedule

        # Background tasks
        self.display_worker_task = None

        # Create pool of FetchRelevantVerse instances
        import dspy

        template_lm = lm if lm is not None else dspy.settings.lm
        if template_lm is None:
            raise RuntimeError("No LM configured")

        self.fetch_verse_pool = []
        pool_size = 2
        for i in range(pool_size):
            analysis_lm = dspy.LM(
                model=template_lm.model,
                **template_lm.kwargs
            )
            self.fetch_verse_pool.append(FetchRelevantVerse(lm=analysis_lm))

        self.pool_semaphore = asyncio.Semaphore(pool_size)
        self.next_pool_idx = 0

        # Create RankVerses module for display worker
        self.rank_verses = dspy.ChainOfThought(RankVerses)

        logger.info(
            f"SermonProcessor initialized with {pool_size} parallel instances "
            f"(session: {self.session_id})"
        )

    def can_display_verse(self) -> bool:
        """Check if enough time has passed since last displayed verse."""
        if self.last_verse_displayed_at is None:
            return True

        time_since = (datetime.now() - self.last_verse_displayed_at).total_seconds()
        can_show = time_since >= self.display_cooldown_seconds
        logger.info(f"Cooldown check: {time_since:.1f}s since last verse (required: {self.display_cooldown_seconds}s) - {'OK' if can_show else 'BLOCKED'}")
        return can_show

    def should_age_queue(self) -> bool:
        """Check if enough time has passed since last queue aging."""
        if self.last_queue_aged_at is None:
            return True

        time_since = (datetime.now() - self.last_queue_aged_at).total_seconds()
        return time_since >= self.display_cooldown_seconds

    def mark_verse_shown(self, reference: str):
        """Mark a verse as recently shown (for duplicate prevention)."""
        if reference not in self.recent_verses:
            self.recent_verses.insert(0, reference)
            # Keep only the most recent N verses
            if len(self.recent_verses) > self.recent_verses_limit:
                self.recent_verses = self.recent_verses[:self.recent_verses_limit]

    def get_recent_verses(self) -> List[str]:
        """Get list of recently shown verses."""
        return self.recent_verses.copy()

    async def process_transcript(self, text: str, timestamp: datetime = None):
        """Process new transcript segment.

        This is the main entry point for the pipeline.
        """
        if not text or not text.strip():
            return

        timestamp = timestamp or datetime.now()

        # Set sermon start time on first segment
        if self.sermon_start_time is None:
            self.sermon_start_time = timestamp
            logger.info(f"Sermon started at {self.sermon_start_time}")

        # ALWAYS broadcast transcript to UI
        await self.ws_server.broadcast_transcript(text, timestamp.isoformat())

        # ALWAYS add to buffer
        self.transcript_buffer.add_segment(text, timestamp)

        # Try to trigger detection (non-blocking)
        asyncio.create_task(self._maybe_detect_and_queue())

    async def _maybe_detect_and_queue(self):
        """Attempt to detect verse and add to queue if enough time has passed."""
        # Check if we have enough content
        word_count = self.transcript_buffer.get_word_count()
        if word_count < 15:
            logger.debug("Not enough words for detection")
            return

        # Check detection interval
        now = datetime.now()
        if self.last_detection_time:
            time_since_last = (now - self.last_detection_time).total_seconds()
            if time_since_last < self.detection_interval_seconds:
                logger.debug(f"Detection interval not reached ({time_since_last:.1f}s < {self.detection_interval_seconds}s)")
                return

        # Update last detection time and run
        self.last_detection_time = now
        await self._detect_and_queue()

    async def _detect_and_queue(self):
        """Fast detection → add to queue (don't display yet)."""
        # Get timestamped context
        current_time = self.transcript_buffer.get_sermon_timestamp(self.sermon_start_time)
        context = self.transcript_buffer.get_timestamped_context(self.sermon_start_time)

        # Format previous verses with timestamps
        previous_verses = "\n".join([
            f"[{event.sermon_timestamp}] {event.verse_reference}"
            for event in self.verse_display_log[-5:]  # Last 5 verses
        ])

        # Format queued verses to prevent re-detection
        queued_verses = "\n".join([item.reference for item in self.verse_queue.queue])

        logger.info(f"Detecting verses at {current_time}...")

        # Get excluded verses
        excluded = self.get_recent_verses()

        # Acquire semaphore to limit concurrent detections
        async with self.pool_semaphore:
            pool_idx = self.next_pool_idx
            self.next_pool_idx = (self.next_pool_idx + 1) % len(self.fetch_verse_pool)
            fetch_verse = self.fetch_verse_pool[pool_idx]

            logger.debug(f"Using FetchRelevantVerse #{pool_idx} from pool")

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            verse_result = await loop.run_in_executor(
                None,
                lambda: fetch_verse(
                    current_time=current_time,
                    context=context,
                    previous_verses=previous_verses,
                    queued_verses=queued_verses,
                    excluded_references=excluded
                )
            )

        # Handle skipped results (ContainsRelevantVerses returned False)
        if verse_result and verse_result.get('skipped'):
            logger.info("No verse detected (skipped by contains check)")
            # Broadcast skip status to frontend
            if self.ws_server:
                await self.ws_server.broadcast_status({
                    'type': 'skip',
                    'reasoning': verse_result.get('reasoning', ''),
                    'retrieval_type': verse_result.get('retrieval_type', 'none'),
                    'timestamp': current_time
                })
            return

        if not verse_result:
            logger.info("No verse detected (error)")
            return

        # Broadcast detection status to frontend (show top candidate reference)
        top_candidate_ref = verse_result.get('candidates', [{}])[0].get('verse_reference', '') if verse_result.get('candidates') else ''
        if self.ws_server:
            await self.ws_server.broadcast_status({
                'type': 'detect',
                'reasoning': verse_result.get('contains_reasoning', ''),
                'best_reference': top_candidate_ref,
                'timestamp': current_time
            })

        # Add top 3 candidates to queue (age-based eviction handles overflow)
        for candidate in verse_result.get('candidates', []):
            self.verse_queue.add_candidate(
                verse_ref=candidate['verse_reference'],
                verse_text=candidate['verse_text'],
                score=candidate['relevance_score'],
                theme=candidate['theme'],
                sermon_time=current_time
            )

        logger.info(f"Added {len(verse_result.get('candidates', []))} candidates to queue")
        logger.info(f"Queue status: {self.verse_queue.get_queue_status()}")

        # Broadcast queue status to frontend
        if self.ws_server:
            queue_data = self.verse_queue.get_candidates_for_ranking()
            await self.ws_server.broadcast_queue(queue_data)

    async def _display_worker(self):
        """Background worker that displays verses from queue after cooldown.

        Runs continuously:
        1. Sleep 1 second
        2. Check if queue has new items since last check
        3. If queue changed AND cooldown elapsed: age queue, re-rank, display
        4. Repeat
        """
        logger.info("Display worker started")

        last_queue_size = 0

        while True:
            try:
                # Always sleep 1 second
                await asyncio.sleep(1)

                # Skip if queue is empty
                if self.verse_queue.is_empty():
                    continue

                # Check if queue has changed (new items added)
                current_queue_size = self.verse_queue.size()
                queue_has_new_items = current_queue_size > last_queue_size
                last_queue_size = current_queue_size

                # Check if we can display (cooldown elapsed)
                can_display = self.can_display_verse()

                # Age queue on its own schedule (separate from display cooldown)
                if self.should_age_queue():
                    self.verse_queue.age_items()
                    self.last_queue_aged_at = datetime.now()
                    # Broadcast queue status after aging
                    if self.ws_server:
                        queue_data = self.verse_queue.get_candidates_for_ranking()
                        await self.ws_server.broadcast_queue(queue_data)

                # Only process if queue has new items
                if not queue_has_new_items:
                    continue

                # Skip if we're still on cooldown
                if not can_display:
                    logger.debug("New items in queue but cooldown active, waiting...")
                    continue

                # Get queue candidates
                candidates = self.verse_queue.get_candidates_for_ranking()
                if not candidates:
                    logger.debug("Queue empty after aging, skipping display cycle")
                    continue

                logger.info(f"Display worker: evaluating {len(candidates)} queued verse(s)")

                # Rank candidates using RankVerses module
                current_time = self.transcript_buffer.get_sermon_timestamp(self.sermon_start_time)
                context = self.transcript_buffer.get_context_window()
                previous_verses = "; ".join(self.get_recent_verses())

                candidates_text = "\n\n".join([
                    f"{i+1}. {c['reference']}\n   \"{c['text']}\""
                    for i, c in enumerate(candidates)
                ])

                ranking = self.rank_verses(
                    current_time=current_time,
                    context=context,
                    previous_verses=previous_verses,
                    candidates=candidates_text
                )

                # Find the ranked verse in candidates
                ranked_ref_lower = ranking.verse_reference.lower()
                best = None
                for candidate in candidates:
                    if candidate['reference'].lower() == ranked_ref_lower:
                        best = candidate
                        best['why_relevant'] = ranking.reasoning
                        best['relevance_score'] = int(ranking.relevance_score)
                        break

                # Fallback to highest voting_score if LLM hallucinated
                if not best:
                    logger.warning(f"LLM ranked '{ranking.verse_reference}' not in queue, falling back to highest voting_score")
                    best = max(candidates, key=lambda x: x['voting_score'])
                    best['why_relevant'] = f"Selected {best['selection_count']} {'time' if best['selection_count'] == 1 else 'times'} in queue"
                    best['relevance_score'] = round(best['score'] * 100)

                # Broadcast ranking decision to status bar
                if self.ws_server:
                    await self.ws_server.broadcast_status({
                        'type': 'ranked',
                        'reference': best['reference'],
                        'score': best.get('relevance_score', 0),
                        'reasoning': best.get('why_relevant', ''),
                        'timestamp': current_time
                    })

                # Check minimum relevance threshold
                # Uses RANKING_CONFIDENCE_THRESHOLD from config
                # Scores below this indicate weak/tangential connection
                min_score = config.RANKING_CONFIDENCE_THRESHOLD
                if best.get('relevance_score', 0) < min_score:
                    logger.info(
                        f"Verse {best['reference']} scored {best['relevance_score']}/100 "
                        f"(below threshold {min_score}), removing from queue"
                    )
                    self.verse_queue.remove_verse(best['reference'])

                    # Broadcast rejection status
                    if self.ws_server:
                        await self.ws_server.broadcast_status({
                            'type': 'rejected',
                            'reference': best['reference'],
                            'score': best.get('relevance_score', 0),
                            'reasoning': f"{best.get('why_relevant', 'Weak match')} (below {min_score}% threshold)",
                            'timestamp': current_time
                        })
                        queue_data = self.verse_queue.get_candidates_for_ranking()
                        await self.ws_server.broadcast_queue(queue_data)
                    continue

                # Check if already shown
                if best['reference'] in self.get_recent_verses():
                    logger.info(f"Verse {best['reference']} already shown, removing from queue")
                    self.verse_queue.remove_verse(best['reference'])

                    # Broadcast rejection status
                    if self.ws_server:
                        await self.ws_server.broadcast_status({
                            'type': 'rejected',
                            'reference': best['reference'],
                            'score': best.get('relevance_score', 0),
                            'reasoning': 'Already displayed recently',
                            'timestamp': current_time
                        })
                        queue_data = self.verse_queue.get_candidates_for_ranking()
                        await self.ws_server.broadcast_queue(queue_data)
                    continue

                # Create display event
                transcript_start, transcript_end = self.transcript_buffer.get_time_range(self.sermon_start_time)
                event = VerseDisplayEvent(
                    verse_reference=best['reference'],
                    verse_text=best['text'],
                    theme=best['theme'],
                    relevance_score=best.get('relevance_score', round(best['score'] * 100)),
                    why_relevant=best.get('why_relevant', f"Selected {best['selection_count']} {'time' if best['selection_count'] == 1 else 'times'} in queue"),
                    displayed_at=datetime.now(),
                    sermon_timestamp=best['sermon_timestamps'][-1],  # Latest detection time
                    sermon_context=self.transcript_buffer.get_context_window(),
                    transcript_start=transcript_start,
                    transcript_end=transcript_end,
                    session_id=self.session_id,
                    selection_count=best['selection_count'],
                    queue_age=best['age']
                )

                # Mark as shown (track for duplicates and set cooldown)
                self.mark_verse_shown(best['reference'])
                self.last_verse_displayed_at = datetime.now()

                # Broadcast to frontend
                await self.ws_server.broadcast_verse(event.to_frontend_data())

                # Log event
                self.verse_display_log.append(event)

                # Remove from queue
                self.verse_queue.remove_verse(best['reference'])

                # Broadcast updated queue after removal (UI needs to see displayed verse removed)
                if self.ws_server:
                    queue_data = self.verse_queue.get_candidates_for_ranking()
                    await self.ws_server.broadcast_queue(queue_data)

                logger.info(
                    f"✓ Verse displayed: {best['reference']} "
                    f"(voting_score: {best['voting_score']:.0f}, selected {best['selection_count']} times)"
                )

                # Update queue size tracker after display
                last_queue_size = self.verse_queue.size()

            except Exception as e:
                logger.error(f"Display worker error: {e}", exc_info=True)
                await asyncio.sleep(5)  # Back off on error

    def start_display_worker(self):
        """Start background display worker task."""
        if self.display_worker_task is None or self.display_worker_task.done():
            self.display_worker_task = asyncio.create_task(self._display_worker())
            logger.info("Display worker task started")
        else:
            logger.warning("Display worker already running")

    def stop_display_worker(self):
        """Stop background display worker task."""
        if self.display_worker_task and not self.display_worker_task.done():
            self.display_worker_task.cancel()
            logger.info("Display worker task stopped")

    def clear_session(self):
        """Clear all session data."""
        self.transcript_buffer.clear()
        self.recent_verses.clear()
        self.verse_queue.clear()
        self.verse_display_log.clear()
        self.sermon_start_time = None
        self.last_verse_displayed_at = None
        self.last_queue_aged_at = None
        logger.info("Session cleared")

    async def handle_sermon_start(self):
        """Handle start of sermon."""
        self.clear_session()
        self.sermon_start_time = datetime.now()
        self.start_display_worker()
        await self.ws_server.broadcast_status('sermon_started', 'Sermon analysis active')
        logger.info("Sermon started")

    async def handle_sermon_end(self):
        """Handle end of sermon."""
        self.stop_display_worker()
        await self.ws_server.broadcast_status('sermon_ended', 'Sermon analysis stopped')
        logger.info(f"Sermon ended - {len(self.verse_display_log)} verses displayed")

        # Log summary
        if self.verse_display_log:
            logger.info("Verse display summary:")
            for event in self.verse_display_log:
                logger.info(
                    f"  [{event.sermon_timestamp}] {event.verse_reference} "
                    f"(score: {event.relevance_score}, selected: {event.selection_count}x)"
                )

    def get_session_summary(self) -> dict:
        """Get summary of current session for analytics."""
        return {
            'session_id': self.session_id,
            'sermon_duration': self.transcript_buffer.get_sermon_timestamp(self.sermon_start_time),
            'verses_displayed': len(self.verse_display_log),
            'queue_size': self.verse_queue.size(),
            'events': [event.to_dict() for event in self.verse_display_log]
        }
