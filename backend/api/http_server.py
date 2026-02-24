"""HTTP API server for receiving audio/transcript input."""

import asyncio
from aiohttp import web
from backend.utils.logger import setup_logger
from backend.processors.sermon_processor import SermonProcessor

logger = setup_logger(__name__)


class HTTPServer:
    """HTTP API server for audio/transcript input."""

    def __init__(self, sermon_processor: SermonProcessor, host="0.0.0.0", port=8080):
        self.sermon_processor = sermon_processor
        self.host = host
        self.port = port
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes."""
        self.app.router.add_post('/api/transcript', self.handle_transcript)
        self.app.router.add_post('/api/audio', self.handle_audio)
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_get('/health', self.handle_health)

        # Enable CORS for browser access
        self.app.middlewares.append(self._cors_middleware)

    @web.middleware
    async def _cors_middleware(self, request, handler):
        """Add CORS headers to all responses."""
        if request.method == "OPTIONS":
            response = web.Response()
        else:
            response = await handler(request)

        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    async def handle_transcript(self, request):
        """
        Handle transcript text input.

        POST /api/transcript
        Body: {"text": "sermon text here", "room": "main-service"}
        """
        try:
            data = await request.json()
            text = data.get('text', '')
            room = data.get('room', 'default')

            if not text:
                return web.json_response(
                    {'error': 'Missing text field'},
                    status=400
                )

            logger.info(f"Received transcript for room '{room}': {text[:100]}...")

            # Process transcript
            await self.sermon_processor.process_transcript(text)

            return web.json_response({
                'status': 'success',
                'message': 'Transcript processed',
                'room': room,
                'length': len(text)
            })

        except Exception as e:
            logger.error(f"Error processing transcript: {e}")
            return web.json_response(
                {'error': str(e)},
                status=500
            )

    async def handle_audio(self, request):
        """
        Handle audio file upload.

        POST /api/audio
        Body: multipart/form-data with 'audio' file and optional 'room' field
        """
        try:
            reader = await request.multipart()
            audio_data = None
            room = 'default'

            async for field in reader:
                if field.name == 'audio':
                    audio_data = await field.read()
                elif field.name == 'room':
                    room = await field.text()

            if not audio_data:
                return web.json_response(
                    {'error': 'Missing audio file'},
                    status=400
                )

            logger.info(f"Received audio for room '{room}': {len(audio_data)} bytes")

            # TODO: Implement audio transcription with Deepgram
            # For now, return not implemented
            return web.json_response({
                'status': 'error',
                'message': 'Audio transcription not yet implemented. Use /api/transcript endpoint for text input.',
                'room': room,
                'audio_size': len(audio_data)
            }, status=501)

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            return web.json_response(
                {'error': str(e)},
                status=500
            )

    async def handle_status(self, request):
        """
        Get system status.

        GET /api/status
        """
        return web.json_response({
            'status': 'running',
            'sermon_active': hasattr(self.sermon_processor, 'session_id'),
            'session_id': getattr(self.sermon_processor, 'session_id', None)
        })

    async def handle_health(self, request):
        """Health check endpoint."""
        return web.json_response({'status': 'ok'})

    async def start(self):
        """Start the HTTP server."""
        logger.info(f"Starting HTTP API server on http://{self.host}:{self.port}")
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        logger.info(f"HTTP API server ready at http://{self.host}:{self.port}")

    async def run(self):
        """Run the HTTP server (blocking)."""
        await self.start()
        # Keep running
        await asyncio.Future()
