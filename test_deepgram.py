import os
from deepgram import DeepgramClient, LiveOptions, LiveTranscriptionEvents
import asyncio

async def test_deepgram():
    try:
        api_key = "35570069ca6048ed71ed0220a647f020daf8609b"
        print(f"Testing with key: {api_key[:10]}...")

        client = DeepgramClient(api_key)
        connection = client.listen.asyncwebsocket.v("1")

        # Track connection state
        events = []

        async def on_open(self, open_event, **kwargs):
            events.append("OPEN")
            print(f"✓ Deepgram WebSocket OPENED: {open_event}")

        async def on_error(self, error, **kwargs):
            events.append(f"ERROR: {error}")
            print(f"✗ Deepgram ERROR: {error}")

        async def on_message(self, result, **kwargs):
            events.append(f"MESSAGE: {result}")
            print(f"→ Deepgram MESSAGE: {result}")

        async def on_close(self, close_event, **kwargs):
            events.append("CLOSE")
            print(f"✗ Deepgram CLOSED: {close_event}")

        connection.on(LiveTranscriptionEvents.Open, on_open)
        connection.on(LiveTranscriptionEvents.Error, on_error)
        connection.on(LiveTranscriptionEvents.Transcript, on_message)
        connection.on(LiveTranscriptionEvents.Close, on_close)

        options = LiveOptions(
            model="nova-2",
            language="en-US",
            encoding="linear16",
            sample_rate=16000,
            channels=1,
            punctuate=True,
            interim_results=False
        )

        print("Starting connection...")
        result = await connection.start(options=options)
        print(f"Start returned: {result}")
        print(f"Is connected: {connection.is_connected}")

        # Wait for connection events
        print("Waiting 5 seconds for events...")
        await asyncio.sleep(5)

        print(f"\nEvents received: {events}")

        if connection.is_connected:
            print("Finishing connection...")
            await connection.finish()

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_deepgram())
