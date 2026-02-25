#!/usr/bin/env python3
"""
Preacher Verse - Real-Time Sermon Verse Retrieval System

Simplified architecture:
- HTTP API receives transcripts from browser (Web Speech API)
- Deepgram SDK available for direct audio transcription
- Gemini LLM via DSPy for verse detection/ranking
- WebSocket broadcasts verses to frontend
"""

import asyncio
import signal
import sys
import dspy

from backend.processors.sermon_processor import SermonProcessor
from backend.services.websocket_server import WebSocketServer
from backend.api.http_server import HTTPServer
from backend.utils.config import config
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

# Global instances
_ws_server: WebSocketServer = None
_http_server: HTTPServer = None
_sermon_processor: SermonProcessor = None
_dspy_lm = None


def setup_dspy_lm():
    """Configure DSPy with Gemini LLM."""
    global _dspy_lm

    if not config.GEMINI_API_KEY:
        logger.error("GEMINI_API_KEY not set in environment")
        sys.exit(1)

    _dspy_lm = dspy.LM(
        model="gemini/gemini-2.0-flash",
        api_key=config.GEMINI_API_KEY,
        max_tokens=8000,
        temperature=0.0
    )
    dspy.configure(lm=_dspy_lm)
    logger.info("DSPy configured with Gemini 2.0 Flash")
    return _dspy_lm


async def start_servers():
    """Start WebSocket and HTTP servers."""
    global _ws_server, _http_server, _sermon_processor

    # Initialize WebSocket server
    _ws_server = WebSocketServer()

    # Initialize sermon processor
    _sermon_processor = SermonProcessor(_ws_server, lm=_dspy_lm)

    # Initialize HTTP server
    _http_server = HTTPServer(
        _sermon_processor,
        host=config.HTTP_HOST,
        port=config.HTTP_PORT
    )

    # Start HTTP server (non-blocking)
    await _http_server.start()

    # Start WebSocket server (blocking - runs forever)
    await _ws_server.start()


async def shutdown():
    """Graceful shutdown."""
    logger.info("Shutting down...")

    if _sermon_processor:
        _sermon_processor.stop_display_worker()

    # Give servers time to close connections
    await asyncio.sleep(0.5)
    logger.info("Shutdown complete")


def handle_signal(sig):
    """Handle shutdown signals."""
    logger.info(f"Received signal {sig}")
    asyncio.create_task(shutdown())


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("Preacher Verse - Starting")
    logger.info("=" * 60)

    # Check required config
    if not config.DEEPGRAM_API_KEY:
        logger.warning("DEEPGRAM_API_KEY not set - direct audio transcription disabled")

    # Setup DSPy/Gemini
    setup_dspy_lm()

    # Register signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: handle_signal(s))

    # Print startup info
    logger.info("")
    logger.info("Services:")
    logger.info(f"  Frontend:   http://localhost:3000")
    logger.info(f"  HTTP API:   http://{config.HTTP_HOST}:{config.HTTP_PORT}")
    logger.info(f"  WebSocket:  ws://{config.WS_HOST}:{config.WS_PORT}")
    logger.info("")
    logger.info("Usage:")
    logger.info("  1. Open http://localhost:3000")
    logger.info("  2. Click 'Connect Microphone'")
    logger.info("  3. Speak - verses will appear automatically")
    logger.info("=" * 60)

    # Start servers (blocks until shutdown)
    try:
        await start_servers()
    except asyncio.CancelledError:
        pass
    finally:
        await shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
