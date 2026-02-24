import asyncio
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.processors.aggregators.sentence import SentenceAggregator
from pipecat.frames.frames import TranscriptionFrame, EndFrame
from pipecat.processors.frame_processor import FrameProcessor

from backend.processors.sermon_processor import SermonProcessor
from backend.services.websocket_server import WebSocketServer
from backend.utils.config import config
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

class TranscriptProcessor(FrameProcessor):
    """Custom processor to handle transcription frames."""

    def __init__(self, sermon_processor: SermonProcessor):
        super().__init__()
        self.sermon_processor = sermon_processor

    async def process_frame(self, frame, direction):
        """Process incoming frames."""
        await super().process_frame(frame, direction)

        # Handle transcription frames
        if isinstance(frame, TranscriptionFrame):
            text = frame.text
            logger.debug(f"Transcription: {text}")

            # Send to sermon processor
            await self.sermon_processor.process_transcript(text)

        # Pass frame through
        await self.push_frame(frame, direction)

class PipecatPipeline:
    """Main Pipecat pipeline for audio processing."""

    def __init__(self, websocket_server: WebSocketServer):
        self.ws_server = websocket_server
        self.sermon_processor = SermonProcessor(websocket_server)

        logger.info("Initializing Pipecat pipeline...")


    async def run_test_mode(self):
        """
        Run in test mode without WebRTC.
        Simulates transcription for testing purposes.
        """
        logger.info("Running in TEST MODE")

        await self.sermon_processor.handle_sermon_start()

        # Simulate sermon segments
        test_segments = [
            "Brothers and sisters, today I want to talk about God's incredible love for us.",
            "You know, sometimes we feel unworthy of His grace.",
            "But the Bible tells us that while we were still sinners, Christ died for us.",
            "This is the heart of the Gospel - unconditional, sacrificial love.",
            "Let me share a story about a time when I felt distant from God.",
            "I was going through a difficult season, full of doubt and fear.",
            "But God reminded me of His faithfulness through His Word.",
            "When we feel afraid, we must remember that perfect love casts out fear.",
            "Jesus is our good shepherd, who laid down His life for the sheep.",
            "We can trust in His promises because He is faithful and true."
        ]

        for i, segment in enumerate(test_segments):
            logger.info(f"[TEST] Segment {i+1}: {segment}")
            await self.sermon_processor.process_transcript(segment)
            await asyncio.sleep(15)  # Simulate 15 seconds between segments

        await self.sermon_processor.handle_sermon_end()
        logger.info("Test mode completed")
