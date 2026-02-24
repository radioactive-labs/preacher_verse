"""FastAPI server for SmallWebRTC prebuilt UI and signaling."""

import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, RedirectResponse
from pipecat_ai_small_webrtc_prebuilt.frontend import SmallWebRTCPrebuiltUI
from backend.utils.logger import setup_logger

logger = setup_logger(__name__)


MAIN_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Preacher Verse - Live Connection</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: #fff;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .header {
            background: rgba(0, 0, 0, 0.3);
            padding: 20px;
            text-align: center;
            border-bottom: 2px solid rgba(255, 255, 255, 0.1);
        }

        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
        }

        .main-content {
            flex: 1;
            display: flex;
            gap: 20px;
            padding: 20px;
            max-width: 1600px;
            width: 100%;
            margin: 0 auto;
        }

        .webrtc-panel {
            flex: 0 0 400px;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }

        .webrtc-panel h2 {
            margin-bottom: 15px;
            color: #ffd700;
        }

        #webrtcFrame {
            width: 100%;
            height: 600px;
            border: none;
            border-radius: 10px;
            background: white;
        }

        .verse-display {
            flex: 1;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            overflow-y: auto;
            max-height: calc(100vh - 200px);
        }

        .verse-display h2 {
            margin-bottom: 20px;
            color: #ffd700;
        }

        .verse-card {
            background: rgba(255, 255, 255, 0.15);
            border-left: 4px solid #ffd700;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            animation: slideIn 0.5s ease-out;
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .verse-reference {
            font-size: 1.3em;
            font-weight: bold;
            color: #ffd700;
            margin-bottom: 15px;
        }

        .verse-text {
            font-size: 1.2em;
            line-height: 1.8;
            margin-bottom: 15px;
            font-style: italic;
        }

        .verse-context {
            font-size: 0.95em;
            opacity: 0.9;
            border-top: 1px solid rgba(255, 255, 255, 0.2);
            padding-top: 15px;
            margin-top: 15px;
        }

        .theme-tag {
            display: inline-block;
            background: rgba(255, 215, 0, 0.3);
            padding: 5px 12px;
            border-radius: 15px;
            margin: 3px;
            font-size: 0.85em;
        }

        .empty-state {
            text-align: center;
            padding: 60px 20px;
            opacity: 0.6;
        }

        .empty-state-icon {
            font-size: 4em;
            margin-bottom: 20px;
        }

        .status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
        }

        .status-disconnected {
            background: #dc3545;
        }

        .status-connected {
            background: #28a745;
        }

        .button {
            padding: 15px;
            border: none;
            border-radius: 8px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s;
        }

        .button-primary {
            background: #28a745;
            color: white;
        }

        .button-primary:hover:not(:disabled) {
            background: #218838;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(40, 167, 69, 0.4);
        }

        .button-danger {
            background: #dc3545;
            color: white;
        }

        .button-danger:hover:not(:disabled) {
            background: #c82333;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(220, 53, 69, 0.4);
        }

        .button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📖 Preacher Verse</h1>
        <span class="status-badge status-disconnected" id="wsStatus">WebSocket Disconnected</span>
    </div>

    <div class="main-content">
        <!-- Voice Input Panel -->
        <div class="webrtc-panel">
            <h2>🎤 Voice Input</h2>
            <div style="padding: 20px;">
                <button class="button button-primary" id="startBtn" onclick="startListening()" style="width: 100%; margin-bottom: 15px;">
                    🎤 Start Listening
                </button>
                <button class="button button-danger" id="stopBtn" onclick="stopListening()" disabled style="width: 100%; margin-bottom: 20px;">
                    🛑 Stop Listening
                </button>

                <div style="background: rgba(0,0,0,0.3); border-radius: 8px; padding: 15px; min-height: 400px; max-height: 400px; overflow-y: auto;">
                    <h3 style="margin-bottom: 10px; color: #ffd700; font-size: 1.1em;">Transcript</h3>
                    <div id="transcript" style="line-height: 1.6; color: rgba(255,255,255,0.9);"></div>
                </div>

                <div style="margin-top: 15px; font-size: 0.9em; opacity: 0.7; line-height: 1.5;">
                    Click "Start Listening" to begin capturing your sermon. The system will analyze your speech and retrieve relevant Bible verses in real-time.
                </div>
            </div>
        </div>

        <!-- Verse Display -->
        <div class="verse-display">
            <h2>📖 Verses</h2>
            <div id="verseContainer">
                <div class="empty-state">
                    <div class="empty-state-icon">📖</div>
                    <h3>Waiting for verses...</h3>
                    <p>Connect your microphone and start speaking.<br>Verses will appear here as they are retrieved.</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        // WebSocket connection for verse notifications
        let ws = null;
        const currentRoom = 'default';

        function connectWebSocket() {
            const wsUrl = 'ws://localhost:8765';
            console.log('Connecting to WebSocket:', wsUrl);

            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                console.log('WebSocket connected');
                document.getElementById('wsStatus').textContent = 'WebSocket Connected';
                document.getElementById('wsStatus').className = 'status-badge status-connected';

                // Join the room
                ws.send(JSON.stringify({
                    type: 'join',
                    room: currentRoom
                }));
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                console.log('WebSocket message:', data);

                if (data.type === 'verse') {
                    displayVerse(data.data);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

            ws.onclose = () => {
                console.log('WebSocket closed');
                document.getElementById('wsStatus').textContent = 'WebSocket Disconnected';
                document.getElementById('wsStatus').className = 'status-badge status-disconnected';

                // Reconnect after 3 seconds
                setTimeout(connectWebSocket, 3000);
            };
        }

        function displayVerse(verseData) {
            const container = document.getElementById('verseContainer');

            // Remove empty state if present
            const emptyState = container.querySelector('.empty-state');
            if (emptyState) {
                emptyState.remove();
            }

            // Create verse card
            const card = document.createElement('div');
            card.className = 'verse-card';

            let html = `
                <div class="verse-reference">${verseData.verse_reference}</div>
                <div class="verse-text">"${verseData.verse_text}"</div>
            `;

            if (verseData.context) {
                html += `
                    <div class="verse-context">
                        <strong>Context:</strong> ${verseData.context}
                    </div>
                `;
            }

            if (verseData.themes && verseData.themes.length > 0) {
                html += `
                    <div class="verse-themes">
                        <strong>Themes:</strong><br>
                        ${verseData.themes.map(theme => `<span class="theme-tag">${theme}</span>`).join('')}
                    </div>
                `;
            }

            card.innerHTML = html;

            // Add to top of container
            container.insertBefore(card, container.firstChild);

            // Keep only last 20 verses
            while (container.children.length > 20) {
                container.removeChild(container.lastChild);
            }
        }

        // Connect when page loads
        connectWebSocket();

        // Web Speech API for voice input
        let recognition = null;
        let transcriptText = '';
        let sendTimer = null;
        let lastSentText = '';

        function startListening() {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                alert('Speech recognition is not supported in this browser. Please use Chrome or Edge.');
                return;
            }

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            recognition.lang = 'en-US';

            recognition.onstart = () => {
                console.log('Speech recognition started');
                document.getElementById('startBtn').disabled = true;
                document.getElementById('stopBtn').disabled = false;
            };

            recognition.onresult = (event) => {
                let interim = '';
                let final = '';

                for (let i = 0; i < event.results.length; i++) {
                    const transcript = event.results[i][0].transcript;
                    if (event.results[i].isFinal) {
                        final += transcript + ' ';
                    } else {
                        interim += transcript;
                    }
                }

                // Update transcript display
                const currentText = transcriptText + final + interim;
                document.getElementById('transcript').textContent = currentText;

                // If we have new finalized text, add it to our transcript
                if (final.trim()) {
                    transcriptText += final;
                }

                // Send updates to backend (debounced)
                clearTimeout(sendTimer);
                sendTimer = setTimeout(() => {
                    if (currentText.trim() && currentText !== lastSentText) {
                        sendTranscriptSegment(currentText.trim());
                        lastSentText = currentText.trim();
                    }
                }, 500);
            };

            recognition.onerror = (event) => {
                console.error('Speech recognition error:', event.error);
                if (event.error === 'no-speech') {
                    // Just continue, don't show alert for no speech
                    console.log('No speech detected, will retry...');
                } else if (event.error === 'aborted') {
                    // User stopped it
                    console.log('Speech recognition aborted');
                } else {
                    console.error('Speech recognition error:', event.error);
                }
            };

            recognition.onend = () => {
                console.log('Speech recognition ended');
                const stopBtn = document.getElementById('stopBtn');
                // Only restart if stop button is still enabled (meaning we want to continue)
                if (stopBtn && !stopBtn.disabled) {
                    // Add a small delay before restarting to prevent rapid loop
                    setTimeout(() => {
                        if (stopBtn && !stopBtn.disabled) {
                            try {
                                recognition.start();
                            } catch (e) {
                                console.error('Failed to restart recognition:', e);
                            }
                        }
                    }, 200);
                }
            };

            recognition.start();
        }

        function stopListening() {
            if (recognition) {
                recognition.stop();
                recognition = null;
            }
            document.getElementById('startBtn').disabled = false;
            document.getElementById('stopBtn').disabled = true;
        }

        async function sendTranscriptSegment(text) {
            try {
                const response = await fetch('http://localhost:8080/api/transcript', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        text: text,
                        room: currentRoom
                    })
                });

                if (!response.ok) {
                    console.error('Failed to send transcript:', response.statusText);
                }
            } catch (error) {
                console.error('Error sending transcript:', error);
            }
        }
    </script>
</body>
</html>
"""


def create_webrtc_app() -> FastAPI:
    """Create FastAPI app with SmallWebRTC prebuilt UI."""
    app = FastAPI(title="Preacher Verse WebRTC")

    # Mount the prebuilt UI at /prebuilt
    app.mount("/prebuilt", SmallWebRTCPrebuiltUI)

    @app.get("/", response_class=HTMLResponse)
    async def root():
        """Serve the main page with WebRTC + verse display."""
        return MAIN_PAGE_HTML

    @app.get("/health")
    async def health():
        """Health check."""
        return {"status": "ok"}

    logger.info("FastAPI WebRTC app created")
    return app
