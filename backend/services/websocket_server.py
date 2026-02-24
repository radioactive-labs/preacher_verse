import asyncio
import websockets
import json
from typing import Set, Dict
from websockets.server import WebSocketServerProtocol
from backend.utils.config import config
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)

class WebSocketServer:
    """WebSocket server for broadcasting verses to frontend clients with room support."""

    def __init__(self):
        # Store clients by room: {room_id: {websocket1, websocket2, ...}}
        self.rooms: Dict[str, Set[WebSocketServerProtocol]] = {}
        # Store which room each websocket is in: {websocket: room_id}
        self.client_rooms: Dict[WebSocketServerProtocol, str] = {}

        self.host = config.WS_HOST
        self.port = config.WS_PORT
        self.heartbeat_interval = config.get('websocket.heartbeat_interval', 30)

        logger.info(f"WebSocket server initialized: {self.host}:{self.port}")

    async def register(self, websocket: WebSocketServerProtocol, room_id: str = "default"):
        """Register a new client connection to a specific room."""
        # Create room if it doesn't exist
        if room_id not in self.rooms:
            self.rooms[room_id] = set()
            logger.info(f"Created new room: {room_id}")

        # Add client to room
        self.rooms[room_id].add(websocket)
        self.client_rooms[websocket] = room_id

        total_clients = sum(len(clients) for clients in self.rooms.values())
        logger.info(f"Client connected to room '{room_id}'. Room: {len(self.rooms[room_id])}, Total: {total_clients}")

        # Send welcome message with server configuration
        await self.send_to_client(websocket, {
            'type': 'connected',
            'message': f'Connected to Preacher Verse server (Room: {room_id})',
            'room': room_id,
            'config': {
                'cooldown_seconds': config.COOLDOWN_SECONDS
            }
        })

    async def unregister(self, websocket: WebSocketServerProtocol):
        """Unregister a client connection."""
        room_id = self.client_rooms.get(websocket)
        if room_id and room_id in self.rooms:
            self.rooms[room_id].discard(websocket)

            # Remove empty rooms
            if len(self.rooms[room_id]) == 0:
                del self.rooms[room_id]
                logger.info(f"Removed empty room: {room_id}")

        self.client_rooms.pop(websocket, None)

        total_clients = sum(len(clients) for clients in self.rooms.values())
        logger.info(f"Client disconnected from room '{room_id}'. Total clients: {total_clients}")

    async def send_to_client(self, websocket: WebSocketServerProtocol, data: dict):
        """Send data to a specific client."""
        try:
            await websocket.send(json.dumps(data))
        except Exception as e:
            logger.error(f"Failed to send to client: {e}")

    async def broadcast_verse(self, verse_data: dict, room_id: str = "default"):
        """Broadcast a verse to all clients in a specific room."""
        message = {
            'type': 'verse',
            'data': verse_data,
            'room': room_id
        }

        room_clients = self.rooms.get(room_id, set())
        logger.info(f"Broadcasting verse to {len(room_clients)} clients in room '{room_id}': {verse_data.get('reference')}")

        # Send to all clients in the room
        if room_clients:
            await asyncio.gather(
                *[self.send_to_client(client, message) for client in room_clients],
                return_exceptions=True
            )

    async def broadcast_queue(self, queue_data: list, room_id: str = "default"):
        """Broadcast queue status to all clients in a specific room."""
        message = {
            'type': 'queue',
            'data': queue_data,
            'room': room_id
        }

        room_clients = self.rooms.get(room_id, set())
        logger.debug(f"Broadcasting queue ({len(queue_data)} items) to {len(room_clients)} clients in room '{room_id}'")

        # Send to all clients in the room
        if room_clients:
            await asyncio.gather(
                *[self.send_to_client(client, message) for client in room_clients],
                return_exceptions=True
            )

    async def broadcast_status(self, status_data: dict, room_id: str = "default"):
        """Broadcast detection status (skip/detect) to all clients in a specific room."""
        message = {
            'type': 'status',
            'data': status_data,
            'room': room_id
        }

        room_clients = self.rooms.get(room_id, set())
        if room_clients:
            await asyncio.gather(
                *[self.send_to_client(client, message) for client in room_clients],
                return_exceptions=True
            )

    async def broadcast(self, data: dict, room_id: str = "default"):
        """Generic broadcast method to send any data to all clients in a specific room."""
        room_clients = self.rooms.get(room_id, set())
        if room_clients:
            await asyncio.gather(
                *[self.send_to_client(client, data) for client in room_clients],
                return_exceptions=True
            )

    async def broadcast_transcript(self, text: str, timestamp: str = None, room_id: str = "default"):
        """Broadcast transcript to all clients in a specific room."""
        from datetime import datetime
        data = {
            'type': 'transcript',
            'data': {
                'text': text,
                'timestamp': timestamp or datetime.now().isoformat()
            }
        }

        room_clients = self.rooms.get(room_id, set())

        if room_clients:
            await asyncio.gather(
                *[self.send_to_client(client, data) for client in room_clients],
                return_exceptions=True
            )

    async def handler(self, websocket: WebSocketServerProtocol):
        """Handle WebSocket connections."""
        # Wait for client to send join message with room_id
        room_id = "default"
        registered = False

        try:
            # Keep connection alive and handle incoming messages
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get('type')

                # Handle join message first
                if msg_type == 'join' and not registered:
                    room_id = data.get('room', 'default')
                    await self.register(websocket, room_id)
                    registered = True
                elif not registered:
                    # Auto-register to default room if client doesn't send join
                    await self.register(websocket, room_id)
                    registered = True

                await self.handle_message(websocket, message)

        except websockets.exceptions.ConnectionClosed:
            logger.info("Client connection closed")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await self.unregister(websocket)

    async def handle_message(self, websocket: WebSocketServerProtocol, message: str):
        """Handle incoming messages from clients."""
        try:
            data = json.loads(message)
            msg_type = data.get('type')

            if msg_type == 'ping':
                await self.send_to_client(websocket, {'type': 'pong'})

            elif msg_type == 'join':
                # Already handled in handler
                pass

            elif msg_type == 'get_status':
                room_id = self.client_rooms.get(websocket, 'default')
                room_clients = len(self.rooms.get(room_id, set()))
                total_clients = sum(len(clients) for clients in self.rooms.values())
                await self.send_to_client(websocket, {
                    'type': 'status',
                    'status': 'running',
                    'room': room_id,
                    'room_clients': room_clients,
                    'total_clients': total_clients
                })

            else:
                logger.warning(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received: {message}")

    async def start(self):
        """Start the WebSocket server."""
        logger.info(f"Starting WebSocket server on ws://{self.host}:{self.port}")

        async with websockets.serve(self.handler, self.host, self.port):
            await asyncio.Future()  # Run forever

    async def heartbeat(self):
        """Send periodic heartbeat to clients."""
        while True:
            await asyncio.sleep(self.heartbeat_interval)

            if self.clients:
                await asyncio.gather(
                    *[self.send_to_client(client, {'type': 'heartbeat'}) for client in self.clients],
                    return_exceptions=True
                )
