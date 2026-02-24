#!/usr/bin/env python3
"""
Preacher Verse - Real-Time Sermon Verse Retrieval System
Main entry point using Pipecat runner with Daily transport.
"""

import asyncio
from typing import AsyncGenerator
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.frames.frames import (
    TranscriptionFrame,
    AudioRawFrame,
    ErrorFrame,
    Frame,
    StartFrame,
    EndFrame,
    CancelFrame
)
from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.services.stt_service import STTService
from pipecat.runner.utils import create_transport
from pipecat.runner.run import main as runner_main
from pipecat.runner.types import RunnerArguments
from pipecat.transports.daily.transport import DailyParams
import numpy as np

import time

from deepgram import (
    DeepgramClient,
    DeepgramClientOptions,
    LiveTranscriptionEvents,
    LiveOptions
)

from backend.processors.sermon_processor import SermonProcessor
from backend.services.websocket_server import WebSocketServer
from backend.utils.config import config
from backend.utils.logger import setup_logger
import dspy
import os

logger = setup_logger(__name__)

# Feature flag: Use V2 queue-based processor
USE_PROCESSOR_V2 = os.getenv("USE_PROCESSOR_V2", "true").lower() == "true"

# Global WebSocket server (shared across all bot sessions)
_ws_server = None
_ws_task = None

# Global DSPy LM (configured once at startup)
_dspy_lm = None


class CustomDeepgramSTTService(STTService):
    """Custom Deepgram STT service that properly sends audio to Deepgram WebSocket."""

    def __init__(self, *, api_key: str, live_options: LiveOptions, **kwargs):
        super().__init__(**kwargs)
        self._api_key = api_key
        self._live_options = live_options
        self._client = None
        self._connection = None
        self._audio_frames_sent = 0
        self._is_connected = False
        self._reconnect_count = 0
        self._max_reconnects = 5
        self._reconnecting = False
        self._should_stop = False  # Flag to prevent reconnection after stop

    async def _connect(self):
        """Establish or re-establish Deepgram WebSocket connection."""
        try:
            # Create new Deepgram client and connection
            self._client = DeepgramClient(self._api_key)
            self._connection = self._client.listen.websocket.v("1")

            # Save reference to service and event loop for callbacks
            service = self
            loop = asyncio.get_running_loop()

            # Set up event handlers (sync callbacks - SDK calls them synchronously)
            def on_open(dg_self, open_event, **kwargs):
                service._is_connected = True
                service._reconnect_count = 0
                logger.info("✓ Deepgram WebSocket opened")

            def on_error(dg_self, error, **kwargs):
                logger.error(f"Deepgram error: {error}")
                # Don't automatically reconnect on error
                service._is_connected = False

            def on_message(dg_self, result, **kwargs):
                try:
                    if result and hasattr(result, 'channel'):
                        alternatives = result.channel.alternatives
                        if alternatives and len(alternatives) > 0:
                            transcript = alternatives[0].transcript
                            if transcript and len(transcript) > 0:
                                # Schedule async push in the captured event loop
                                future = asyncio.run_coroutine_threadsafe(
                                    service.push_frame(TranscriptionFrame(
                                        text=transcript,
                                        user_id="user",
                                        timestamp=str(time.time())
                                    ), FrameDirection.DOWNSTREAM),
                                    loop
                                )
                except Exception as e:
                    logger.error(f"Error processing transcript: {e}")

            def on_close(dg_self, close_event, **kwargs):
                logger.info(f"Deepgram WebSocket closed: {close_event}")
                service._is_connected = False
                # Don't auto-reconnect - let Pipecat's idle timeout handle cleanup
                # Auto-reconnect was causing infinite loops when room is empty

            # Register event handlers
            self._connection.on(LiveTranscriptionEvents.Open, on_open)
            self._connection.on(LiveTranscriptionEvents.Error, on_error)
            self._connection.on(LiveTranscriptionEvents.Transcript, on_message)
            self._connection.on(LiveTranscriptionEvents.Close, on_close)

            # Start the connection
            logger.info(f"Starting Deepgram connection with options: {self._live_options}")
            start_result = self._connection.start(self._live_options)
            if asyncio.iscoroutine(start_result):
                success = await start_result
            else:
                success = start_result

            if success:
                logger.info("✓ Deepgram connection started successfully")
                return True
            else:
                logger.error("✗ Failed to start Deepgram connection")
                return False

        except Exception as e:
            logger.error(f"Error connecting to Deepgram: {e}")
            return False

    async def _reconnect(self):
        """Attempt to reconnect to Deepgram."""
        # Don't reconnect if we're stopping
        if self._should_stop:
            logger.info("Service is stopping, skipping reconnection")
            return

        if self._reconnecting:
            return  # Already reconnecting

        self._reconnecting = True
        self._reconnect_count += 1

        if self._reconnect_count > self._max_reconnects:
            logger.error(f"Max reconnection attempts ({self._max_reconnects}) reached. Giving up.")
            self._reconnecting = False
            self._reconnect_count = 0  # Reset for potential future reconnections
            return

        logger.info(f"Attempting to reconnect to Deepgram (attempt {self._reconnect_count}/{self._max_reconnects})...")

        # Close existing connection if any
        if self._connection:
            try:
                finish_result = self._connection.finish()
                if asyncio.iscoroutine(finish_result):
                    await finish_result
            except Exception as e:
                logger.debug(f"Error closing old connection: {e}")

        # Wait before reconnecting (exponential backoff)
        wait_time = min(2 ** self._reconnect_count, 30)  # Max 30 seconds
        logger.info(f"Waiting {wait_time}s before reconnection...")
        await asyncio.sleep(wait_time)

        # Attempt reconnection
        success = await self._connect()

        if success:
            logger.info(f"✓ Reconnection successful!")
            # Reset count is handled in on_open callback
        else:
            logger.error(f"✗ Reconnection failed")
            # Don't reset count - will retry with higher backoff

        self._reconnecting = False

    async def start(self, frame: StartFrame):
        """Initialize Deepgram WebSocket connection."""
        await super().start(frame)
        await self._connect()

    async def stop(self, frame: EndFrame):
        """Clean up Deepgram connection."""
        logger.info(f"Stopping Deepgram (sent {self._audio_frames_sent} audio frames)")

        # Set flag to prevent reconnection attempts
        self._should_stop = True
        self._is_connected = False

        if self._connection:
            try:
                finish_result = self._connection.finish()
                if asyncio.iscoroutine(finish_result):
                    await finish_result
            except Exception as e:
                logger.error(f"Error finishing Deepgram connection: {e}")
        await super().stop(frame)

    async def cancel(self, frame: CancelFrame):
        """Handle cancellation."""
        await self.stop(frame)
        await super().cancel(frame)

    async def run_stt(self, audio: bytes) -> AsyncGenerator[Frame, None]:
        """Send audio data to Deepgram for transcription."""
        if self._connection and self._is_connected and len(audio) > 0:
            try:
                self._audio_frames_sent += 1

                # Log first few frames to verify audio is being sent
                if self._audio_frames_sent <= 3:
                    logger.info(f"Sending audio frame {self._audio_frames_sent} to Deepgram: {len(audio)} bytes")
                elif self._audio_frames_sent % 100 == 0:
                    logger.info(f"Sent {self._audio_frames_sent} audio frames to Deepgram")

                # Send audio to Deepgram
                send_result = self._connection.send(audio)
                if asyncio.iscoroutine(send_result):
                    await send_result

            except Exception as e:
                logger.error(f"Error sending audio to Deepgram: {type(e).__name__}: {e}")
                self._is_connected = False
                await self.push_frame(ErrorFrame(error=str(e)))

        # Yield None as transcriptions come via WebSocket callbacks
        yield None


async def _ensure_websocket_server():
    """Ensure WebSocket server is running (singleton)."""
    global _ws_server, _ws_task
    # WebSocket server is already running in background thread
    # Just return the reference
    if _ws_server is None:
        raise RuntimeError("WebSocket server not initialized!")
    return _ws_server


def _ensure_dspy_lm():
    """Ensure DSPy LM is configured (singleton)."""
    global _dspy_lm
    if _dspy_lm is None:
        # Using Gemini 2.0 Flash (no thinking mode) for consistent low latency
        # 2.5 Flash has thinking mode that cannot be reliably disabled
        _dspy_lm = dspy.LM(
            model="gemini/gemini-2.0-flash",
            api_key=config.GEMINI_API_KEY,
            max_tokens=8000,
            temperature=0.0
        )
        dspy.configure(lm=_dspy_lm)
        logger.info("DSPy LM initialized with Gemini 2.0 Flash (no thinking mode)")
    return _dspy_lm


class TranscriptProcessor(FrameProcessor):
    """Custom processor to handle transcription frames and send to sermon processor."""

    def __init__(self, sermon_processor: SermonProcessor):
        super().__init__()
        self.sermon_processor = sermon_processor
        self.audio_frame_count = 0
        self.last_log_time = 0
        self.last_keepalive_time = 0

    async def process_frame(self, frame, direction):
        """Process incoming frames."""
        await super().process_frame(frame, direction)
        from pipecat.frames.frames import AudioRawFrame, ErrorFrame, TranscriptionFrame, UserSpeakingFrame
        import time

        current_time = time.time()

        if isinstance(frame, AudioRawFrame):
            self.audio_frame_count += 1
            # Calculate RMS to check audio volume
            audio_np = np.frombuffer(frame.audio, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_np.astype(np.float64)**2)) if len(audio_np) > 0 else 0.0
            if self.audio_frame_count <= 5:
                logger.info(f"Sample audio frame: len={len(frame.audio)}, RMS={rms:.2f}")
            if current_time - self.last_log_time > 5:
                logger.info(f"Audio frames received: {self.audio_frame_count}, RMS={rms:.2f}")
                self.last_log_time = current_time

            # Send keepalive UserSpeakingFrame every 60 seconds to prevent idle timeout
            # This tells Pipecat that the user is still active even without transcripts
            if current_time - self.last_keepalive_time > 60:
                await self.push_frame(UserSpeakingFrame(), direction)
                self.last_keepalive_time = current_time
                logger.debug("Sent keepalive UserSpeakingFrame")

        if isinstance(frame, ErrorFrame):
            logger.error(f"Error frame: {frame.error}")
        if isinstance(frame, TranscriptionFrame):
            # Send transcription to sermon processor for verse retrieval
            await self.sermon_processor.process_transcript(frame.text)
        await self.push_frame(frame, direction)

# Transport configuration
transport_params = {
    "daily": lambda: DailyParams(
        audio_in_enabled=True,
        audio_out_enabled=False,
        video_in_enabled=False,
        video_out_enabled=False,
        api_key=config.DAILY_API_KEY,
    )
}

async def create_stt():
    """Create and return custom Deepgram STT service."""
    deepgram_options = LiveOptions(
        model="nova-2",
        language="en-US",
        encoding="linear16",
        sample_rate=16000,
        channels=1,
        punctuate=True,
        interim_results=False,  # Only final transcripts
        profanity_filter=True,
        smart_format=True,
        vad_events=False,
        endpointing=1000,  # Wait 1 second of silence before finalizing
    )

    return CustomDeepgramSTTService(
        api_key=config.DEEPGRAM_API_KEY,
        live_options=deepgram_options
    )

async def bot(runner_args: RunnerArguments):
    """
    Main bot function - compatible with Pipecat runner.

    This function is called by the Pipecat runner when a client connects.
    """
    logger.info("=" * 60)
    logger.info("Preacher Verse Bot - Starting Session")
    logger.info("=" * 60)

    # Get or create shared WebSocket server
    ws_server = await _ensure_websocket_server()

    # Get or create shared DSPy LM
    lm = _ensure_dspy_lm()

    # Initialize sermon processor for this session
    sermon_processor = SermonProcessor(ws_server, lm=lm)

    # Create transport using Pipecat runner utilities
    transport = await create_transport(runner_args, transport_params)

    
    stt = await create_stt()

    # Create processors
    transcript_processor = TranscriptProcessor(sermon_processor)

    # Build pipeline (removed SentenceAggregator since we get complete sentences from Deepgram)
    pipeline = Pipeline([
        transport.input(),
        stt,
        transcript_processor,
        transport.output()
    ])

    # Create task
    task = PipelineTask(pipeline)

    # Notify sermon start
    await sermon_processor.handle_sermon_start()

    # Run pipeline
    logger.info("Starting sermon processing pipeline...")
    runner = PipelineRunner()

    try:
        await runner.run(task)
    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
    finally:
        await sermon_processor.handle_sermon_end()
        logger.info("Session ended")


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("Preacher Verse - Starting")
    logger.info("=" * 60)
    logger.info(f"Processor Version: {'V2 (queue-based)' if USE_PROCESSOR_V2 else 'V1 (legacy)'}")
    logger.info(f"Feature flag USE_PROCESSOR_V2={USE_PROCESSOR_V2}")

    # Initialize global WebSocket server
    _ws_server = WebSocketServer()

    # Start WebSocket server in a background thread
    import threading
    def start_ws():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_ws_server.start())

    ws_thread = threading.Thread(target=start_ws, daemon=True)
    ws_thread.start()

    import time
    time.sleep(1)  # Give WebSocket time to start

    logger.info("WebSocket server started on ws://0.0.0.0:8765")
    logger.info("Daily Bot: http://localhost:7860")
    logger.info("WebSocket:  ws://localhost:8765")
    logger.info("=" * 60)

    # Use Pipecat's runner with Daily transport
    import sys
    sys.argv.extend(["-t", "daily"])  # Use Daily transport
    runner_main()
