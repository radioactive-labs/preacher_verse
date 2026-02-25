import { useState, useRef, useEffect } from 'react';

function AudioConfigPanel({ queuedVerses = [] }) {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState(null);
  const [audioLevel, setAudioLevel] = useState(0);

  const recognitionRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animationFrameRef = useRef(null);
  const mediaStreamRef = useRef(null);

  const startConnection = async () => {
    try {
      setError(null);
      setIsConnecting(true);

      // Check for Web Speech API support
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (!SpeechRecognition) {
        throw new Error('Speech recognition not supported. Use Chrome or Edge.');
      }

      // Request microphone access for audio visualization
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      // Set up audio visualization
      setupAudioVisualization(stream);

      // Set up speech recognition
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onstart = () => {
        console.log('[Speech] Recognition started');
        setIsConnecting(false);
        setIsConnected(true);
      };

      recognition.onresult = async (event) => {
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          }
        }

        // Send final transcripts to backend
        if (finalTranscript.trim()) {
          await sendTranscript(finalTranscript.trim());
        }
      };

      recognition.onerror = (event) => {
        console.error('[Speech] Error:', event.error);
        if (event.error !== 'no-speech' && event.error !== 'aborted') {
          setError(`Speech error: ${event.error}`);
        }
      };

      recognition.onend = () => {
        console.log('[Speech] Recognition ended');
        // Auto-restart if still connected
        if (recognitionRef.current && isConnected) {
          setTimeout(() => {
            try {
              recognitionRef.current?.start();
            } catch (e) {
              console.error('[Speech] Failed to restart:', e);
            }
          }, 100);
        }
      };

      recognitionRef.current = recognition;
      recognition.start();

    } catch (err) {
      console.error('[Audio] Failed to start:', err);
      setError(err.message);
      setIsConnecting(false);
    }
  };

  const setupAudioVisualization = (stream) => {
    try {
      audioContextRef.current = new (window.AudioContext || window.webkitAudioContext)();
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 256;

      const source = audioContextRef.current.createMediaStreamSource(stream);
      source.connect(analyserRef.current);

      console.log('[Visualization] Started with real audio');
      updateAudioLevel();
    } catch (err) {
      console.error('[Visualization] Failed:', err);
    }
  };

  const updateAudioLevel = () => {
    if (!analyserRef.current) {
      return;
    }

    const dataArray = new Uint8Array(analyserRef.current.frequencyBinCount);
    analyserRef.current.getByteFrequencyData(dataArray);

    // Calculate average level
    const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
    const level = Math.min(100, (average / 128) * 100);

    setAudioLevel(level);
    animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
  };

  const sendTranscript = async (text) => {
    try {
      const response = await fetch('http://localhost:8080/api/transcript', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, room: 'default' })
      });

      if (!response.ok) {
        console.error('[Transcript] Failed to send:', response.statusText);
      }
    } catch (err) {
      console.error('[Transcript] Error:', err);
    }
  };

  const stopConnection = () => {
    console.log('[Audio] Stopping...');

    // Stop recognition
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }

    // Stop visualization
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    // Close audio context
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    // Stop media stream
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }

    setAudioLevel(0);
    setIsConnected(false);
    setIsConnecting(false);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopConnection();
    };
  }, []);

  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-white">
        <h2 className="text-lg font-semibold text-gray-900">Audio Control</h2>
        <p className="text-xs text-gray-600 mt-1">Connect microphone to start</p>
      </div>

      {/* Voice Controls */}
      <div className="flex-1 overflow-y-auto p-6 bg-white">
        <div className="space-y-6">
          {/* Connection Button */}
          <div className="flex justify-center">
            {isConnecting ? (
              <button
                disabled
                className="px-6 py-3 bg-gray-400 text-white rounded-lg font-medium cursor-not-allowed"
              >
                Connecting...
              </button>
            ) : !isConnected ? (
              <button
                onClick={startConnection}
                className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
              >
                Connect Microphone
              </button>
            ) : (
              <button
                onClick={stopConnection}
                className="px-6 py-3 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
              >
                Disconnect
              </button>
            )}
          </div>

          {/* Audio Visualizer */}
          {isConnected && (
            <div className="space-y-2">
              <label className="text-sm font-medium text-gray-700">
                Audio Level
              </label>
              <div className="w-full bg-gray-200 rounded-full h-3">
                <div
                  className="bg-primary-600 h-3 rounded-full transition-all duration-100"
                  style={{ width: `${audioLevel}%` }}
                />
              </div>
            </div>
          )}

          {/* Error Display */}
          {error && (
            <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {/* Status */}
          <div className="text-center">
            <p className="text-sm text-gray-600">
              {isConnecting ? 'Connecting...' : isConnected ? 'Connected - Speak now' : 'Not connected'}
            </p>
          </div>
        </div>
      </div>

      {/* Queue Section */}
      <div className="border-t border-gray-200">
        <div className="px-6 py-3 bg-gray-50">
          <h3 className="text-sm font-semibold text-gray-900">
            Verse Queue ({queuedVerses.length})
          </h3>
          <p className="text-xs text-gray-600 mt-0.5">Pending display</p>
        </div>

        <div className="overflow-y-auto max-h-96">
          {queuedVerses.length === 0 ? (
            <div className="px-6 py-8 text-center">
              <p className="text-sm text-gray-500">No verses queued</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100">
              {queuedVerses.map((item) => (
                <div
                  key={item.reference}
                  className="px-6 py-3 hover:bg-gray-50 transition-colors"
                >
                  {/* Reference and Badges */}
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-gray-900 text-sm">
                      {item.reference}
                    </span>
                    <div className="flex items-center gap-1">
                      <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs rounded-full font-medium">
                        votes: {item.selection_count}
                      </span>
                      <span className="px-2 py-0.5 bg-purple-100 text-purple-700 text-xs rounded-full font-medium">
                        {Math.round(item.voting_score)}
                      </span>
                      <span className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded-full font-medium">
                        age: {item.age}
                      </span>
                    </div>
                  </div>

                  {/* Verse Text Preview */}
                  <p className="text-xs text-gray-600 italic line-clamp-2 mb-2">
                    "{item.text}"
                  </p>

                  {/* Timestamps */}
                  {item.sermon_timestamps && item.sermon_timestamps.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {item.sermon_timestamps.map((ts, i) => (
                        <span
                          key={i}
                          className="px-1.5 py-0.5 bg-gray-100 text-gray-600 text-xs rounded font-mono"
                        >
                          {ts}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AudioConfigPanel;
