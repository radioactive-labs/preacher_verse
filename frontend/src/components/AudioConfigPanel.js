import { useState, useRef, useEffect } from 'react';
import DailyIframe from '@daily-co/daily-js';

function AudioConfigPanel({ queuedVerses = [] }) {
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState(null);
  const [audioLevel, setAudioLevel] = useState(0);

  const dailyRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyserRef = useRef(null);
  const animationFrameRef = useRef(null);

  const startConnection = async () => {
    try {
      setError(null);
      setIsConnecting(true);

      // Clean up any existing Daily instance first
      if (dailyRef.current) {
        console.log('[Daily] Cleaning up existing instance...');
        try {
          await dailyRef.current.destroy();
        } catch (e) {
          console.warn('[Daily] Error destroying existing instance:', e);
        }
        dailyRef.current = null;
      }

      console.log('[Daily] Creating Daily call object...');

      // Create Daily call object
      const daily = DailyIframe.createCallObject({
        audioSource: true,
        videoSource: false,
      });

      dailyRef.current = daily;

      // Set up event listeners
      daily.on('joined-meeting', () => {
        console.log('[Daily] Joined meeting');
        setIsConnecting(false);
        setIsConnected(true);
        setupAudioVisualization();
      });

      daily.on('left-meeting', () => {
        console.log('[Daily] Left meeting');
        setIsConnected(false);
      });

      daily.on('error', (error) => {
        console.error('[Daily] Error:', error);
        setError(error.errorMsg || 'Daily connection failed');
        setIsConnecting(false);
      });

      // Request room from backend
      console.log('[Daily] Requesting room from backend...');
      const response = await fetch('http://localhost:7860/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
      });

      if (!response.ok) {
        throw new Error(`Failed to create room: ${response.status}`);
      }

      const data = await response.json();
      const roomUrl = data.dailyRoom;
      const token = data.dailyToken;

      console.log('[Daily] Room URL:', roomUrl);
      console.log('[Daily] Token received');

      // Join the Daily room
      await daily.join({
        url: roomUrl,
        token: token
      });

      console.log('[Daily] Join request sent');

    } catch (err) {
      console.error('[Daily] Failed to start:', err);
      setError(err.message);
      setIsConnecting(false);
    }
  };

  const setupAudioVisualization = async () => {
    try {
      // Use simulated visualization (safer for now)
      updateAudioLevel();
      console.log('[Visualization] Started (simulated)');
    } catch (err) {
      console.error('[Visualization] Failed to setup:', err);
      updateAudioLevel();
    }
  };

  const updateAudioLevel = () => {
    // Simulated audio levels
    const simulatedLevel = 30 + Math.random() * 40;
    setAudioLevel(simulatedLevel);

    animationFrameRef.current = requestAnimationFrame(updateAudioLevel);
  };

  const stopConnection = async () => {
    console.log('[Daily] Stopping connection...');

    // Stop visualization
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }

    // Leave Daily call
    if (dailyRef.current) {
      await dailyRef.current.leave();
      await dailyRef.current.destroy();
      dailyRef.current = null;
    }

    setAudioLevel(0);
    setIsConnected(false);
    setIsConnecting(false);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (dailyRef.current) {
        dailyRef.current.destroy();
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
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
              {queuedVerses.map((item, index) => (
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
