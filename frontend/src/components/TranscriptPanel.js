import React from 'react';

function TranscriptPanel({ transcript, cooldownActive, cooldownRemaining, cooldownDuration }) {
  return (
    <div className="h-full flex flex-col bg-white">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Live Transcript</h2>
      </div>

      {/* Cooldown Indicator */}
      {cooldownActive && (
        <div className="mx-6 mt-4 p-4 bg-amber-50 border border-amber-200 rounded-lg">
          <div className="flex items-center gap-3">
            <div className="flex-shrink-0">
              <svg className="w-5 h-5 text-amber-600 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="flex-1">
              <p className="text-sm font-medium text-amber-800">Cooldown Active</p>
              <p className="text-xs text-amber-700 mt-0.5">{cooldownRemaining}s until next verse</p>
            </div>
          </div>
          <div className="mt-3 h-1.5 bg-amber-100 rounded-full overflow-hidden">
            <div
              className="h-full bg-amber-500 transition-all duration-1000 ease-linear"
              style={{ width: `${(cooldownRemaining / (cooldownDuration || 60)) * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* Transcript */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {transcript.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-gray-600">Waiting for audio...</p>
            <p className="text-xs text-gray-500 mt-1">Start speaking to see transcript</p>
          </div>
        ) : (
          <div className="space-y-3">
            {transcript.map((item, index) => (
              <div
                key={index}
                className="p-3 bg-gray-50 rounded-lg border border-gray-200 animate-fade-in"
              >
                <div className="flex items-start gap-2">
                  <span className="text-xs text-gray-500 mt-0.5">{item.timestamp}</span>
                  <p className="text-sm text-gray-800 flex-1 leading-relaxed">{item.text}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Stats Footer */}
      <div className="px-6 py-3 border-t border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-600">Words: {transcript.reduce((acc, item) => acc + item.text.split(' ').length, 0)}</span>
          <span className="text-gray-600">Segments: {transcript.length}</span>
        </div>
      </div>
    </div>
  );
}

export default TranscriptPanel;
