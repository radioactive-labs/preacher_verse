import React, { useState, useEffect, useRef } from 'react';
import AudioConfigPanel from './components/AudioConfigPanel';
import VersesPanel from './components/VersesPanel';
import TranscriptPanel from './components/TranscriptPanel';

const WS_URL = 'ws://localhost:8765';
const RECONNECT_DELAY = 5000;
const MAX_RECONNECT_ATTEMPTS = 5;

function App() {
  const [connected, setConnected] = useState(false);
  const [verses, setVerses] = useState([]);
  const [queuedVerses, setQueuedVerses] = useState([]);
  const [transcript, setTranscript] = useState([]);
  const [cooldownActive, setCooldownActive] = useState(false);
  const [cooldownRemaining, setCooldownRemaining] = useState(0);
  const [detectionStatus, setDetectionStatus] = useState(null);
  const [cooldownDuration, setCooldownDuration] = useState(60); // Default, will be updated from server

  const wsRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef(null);
  const cooldownIntervalRef = useRef(null);

  // WebSocket connection
  useEffect(() => {
    let mounted = true;

    const connect = () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      if (!mounted || reconnectAttemptsRef.current >= MAX_RECONNECT_ATTEMPTS) {
        return;
      }

      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }

      console.log(`Connecting to ${WS_URL}... (attempt ${reconnectAttemptsRef.current + 1})`);

      try {
        const websocket = new WebSocket(WS_URL);

        websocket.onopen = () => {
          if (!mounted) {
            websocket.close();
            return;
          }

          console.log('WebSocket connected');
          setConnected(true);
          reconnectAttemptsRef.current = 0;

          websocket.send(JSON.stringify({
            type: 'join',
            room: 'default'
          }));
        };

        websocket.onmessage = (event) => {
          if (!mounted) return;

          try {
            const data = JSON.parse(event.data);

            if (data.type === 'connected') {
              console.log('Connected to server:', data.message);
              // Update cooldown duration from server config
              if (data.config && data.config.cooldown_seconds) {
                setCooldownDuration(data.config.cooldown_seconds);
                console.log('Cooldown duration set to:', data.config.cooldown_seconds, 'seconds');
              }
            } else if (data.type === 'verse') {
              console.log('Received verse:', data.data.reference);
              // Add new verse
              setVerses(prev => [data.data, ...prev].slice(0, 20));

              // Start cooldown
              startCooldown();
            } else if (data.type === 'queue') {
              console.log('Received queue update:', data.data.length, 'items');
              // Update queued verses
              setQueuedVerses(data.data);
            } else if (data.type === 'status') {
              console.log('Received detection status:', data.data.type);
              // Update detection status
              setDetectionStatus(data.data);
            } else if (data.type === 'transcript') {
              console.log('Received transcript:', data.data.text.substring(0, 50) + '...');
              // Add transcript segment
              setTranscript(prev => [
                {
                  text: data.data.text,
                  timestamp: new Date().toLocaleTimeString()
                },
                ...prev
              ].slice(0, 50));
            }
          } catch (err) {
            console.error('Failed to parse message:', err);
          }
        };

        websocket.onerror = (error) => {
          console.error('WebSocket error:', error);
        };

        websocket.onclose = () => {
          if (!mounted) return;

          console.log('WebSocket disconnected');
          setConnected(false);
          wsRef.current = null;

          reconnectAttemptsRef.current++;
          if (reconnectAttemptsRef.current < MAX_RECONNECT_ATTEMPTS) {
            console.log(`Will reconnect in ${RECONNECT_DELAY / 1000}s...`);
            reconnectTimeoutRef.current = setTimeout(connect, RECONNECT_DELAY);
          } else {
            console.log('Max reconnect attempts reached');
          }
        };

        wsRef.current = websocket;
      } catch (err) {
        console.error('Failed to create WebSocket:', err);
      }
    };

    connect();

    return () => {
      mounted = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (cooldownIntervalRef.current) {
        clearInterval(cooldownIntervalRef.current);
      }
    };
  }, []);

  const startCooldown = () => {
    setCooldownActive(true);
    setCooldownRemaining(cooldownDuration);

    if (cooldownIntervalRef.current) {
      clearInterval(cooldownIntervalRef.current);
    }

    cooldownIntervalRef.current = setInterval(() => {
      setCooldownRemaining(prev => {
        if (prev <= 1) {
          clearInterval(cooldownIntervalRef.current);
          setCooldownActive(false);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  return (
    <div className="h-screen bg-white flex flex-col overflow-hidden">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-600 flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-semibold text-gray-900">Preacher Verse</h1>
              <p className="text-xs text-gray-600">Real-time sermon verse retrieval</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${connected
                ? 'bg-emerald-500/10 border border-emerald-500/20'
                : 'bg-red-500/10 border border-red-500/20'
              }`}>
              <div className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'
                }`}></div>
              <span className={`text-xs font-medium ${connected ? 'text-emerald-400' : 'text-red-400'
                }`}>
                {connected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* 3-Column Layout */}
      <div className="flex-1 grid grid-cols-12 gap-0 overflow-hidden bg-gray-50">
        {/* Left: Audio Config + Queue (3 columns) */}
        <div className="col-span-3 border-r border-gray-200 overflow-hidden bg-white">
          <AudioConfigPanel queuedVerses={queuedVerses} />
        </div>

        {/* Center: Verses (6 columns) */}
        <div className="col-span-6 border-r border-gray-200 overflow-hidden bg-gray-50">
          <VersesPanel verses={verses} />
        </div>

        {/* Right: Transcript (3 columns) */}
        <div className="col-span-3 overflow-hidden bg-white">
          <TranscriptPanel
            transcript={transcript}
            cooldownActive={cooldownActive}
            cooldownRemaining={cooldownRemaining}
            cooldownDuration={cooldownDuration}
          />
        </div>
      </div>

      {/* Status Bar - Bottom */}
      {detectionStatus && (
        <div className={`px-6 py-2 text-sm border-t ${
          detectionStatus.type === 'skip'
            ? 'bg-gray-50 border-gray-200'
            : detectionStatus.type === 'ranked'
            ? 'bg-purple-50 border-purple-200'
            : detectionStatus.type === 'rejected'
            ? 'bg-red-50 border-red-200'
            : 'bg-blue-50 border-blue-200'
        }`}>
          <div className="flex items-center gap-3">
            <span className="font-mono text-xs text-gray-500">{detectionStatus.timestamp}</span>
            <span className={`font-semibold ${
              detectionStatus.type === 'skip'
                ? 'text-gray-700'
                : detectionStatus.type === 'ranked'
                ? 'text-purple-700'
                : detectionStatus.type === 'rejected'
                ? 'text-red-700'
                : 'text-blue-700'
            }`}>
              {detectionStatus.type === 'skip' && '⊘ Skipped'}
              {detectionStatus.type === 'detect' && '✓ Detected'}
              {detectionStatus.type === 'ranked' && `⭐ Ranked: ${detectionStatus.reference}`}
              {detectionStatus.type === 'rejected' && `✗ Rejected: ${detectionStatus.reference}`}
              {detectionStatus.type === 'detect' && detectionStatus.best_reference && `: ${detectionStatus.best_reference}`}
              {(detectionStatus.type === 'ranked' || detectionStatus.type === 'rejected') && ` (${detectionStatus.score}%)`}
            </span>
            <span className="text-gray-600 truncate flex-1" title={detectionStatus.reasoning}>
              {detectionStatus.reasoning}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
