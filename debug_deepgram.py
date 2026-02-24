import asyncio
import wave
from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions

API_KEY = "35570069ca6048ed71ed0220a647f020daf8609b"  # Replace with fresh key from Deepgram Console
deepgram_options = LiveOptions(
    model="nova-2",
    language="en-US",
    encoding="linear16",
    sample_rate=16000,
    channels=1,
    punctuate=True,
    interim_results=True,
    profanity_filter=True,
    smart_format=True,
    vad_events=True
)

async def debug_connect():
    try:
        deepgram = DeepgramClient(api_key=API_KEY)
        connection = deepgram.listen.websocket.v("1")

        def on_open(self, *args, **kwargs):
            print("✅ Deepgram WebSocket opened")
        def on_error(self, *args, **kwargs):
            print(f"❌ Deepgram error: {kwargs.get('error')}")
        def on_close(self, *args, **kwargs):
            print(f"Deepgram closed: code={kwargs.get('code')} reason={kwargs.get('reason')}")
        def on_transcript(self, *args, **kwargs):
            transcript = kwargs.get('result', {}).get('channel', {}).get('alternatives', [{}])[0].get('transcript', '')
            if transcript:
                print(f"Transcription: {transcript}")
        def on_speech_started(self, *args, **kwargs):
            print("VAD: SpeechStarted")
        def on_utterance_end(self, *args, **kwargs):
            print("VAD: UtteranceEnd")

        connection.on(LiveTranscriptionEvents.Open, on_open)
        connection.on(LiveTranscriptionEvents.Error, on_error)
        connection.on(LiveTranscriptionEvents.Close, on_close)
        connection.on(LiveTranscriptionEvents.Transcript, on_transcript)
        connection.on(LiveTranscriptionEvents.SpeechStarted, on_speech_started)
        connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)

        # Start connection, handle non-awaitable
        result = connection.start(deepgram_options)
        if asyncio.iscoroutine(result):
            await result
        print("Connection started")
        
        # Send test.wav audio
        with wave.open("test.wav", "rb") as wav:
            if wav.getframerate() != 16000 or wav.getnchannels() != 1:
                print("❌ WAV must be 16kHz mono")
                return
            chunk = wav.readframes(3200)  # 100ms chunks
            while chunk:
                await connection.send(chunk)
                await asyncio.sleep(0.1)
                chunk = wav.readframes(3200)
        
        await asyncio.sleep(5)
        await connection.finish()
        print("Test complete")
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {e}")

asyncio.run(debug_connect())