import React from 'react';
import VerseDisplay from './VerseDisplay';

function VersesPanel({ verses }) {
  return (
    <div className="h-full flex flex-col bg-gray-50">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 bg-white">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Displayed Verses</h2>
            <p className="text-xs text-gray-600 mt-1">
              {verses.length} verses shown
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-primary-500 animate-pulse"></div>
            <span className="text-xs text-gray-600">Live</span>
          </div>
        </div>
      </div>

      {/* Displayed Verses List */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {verses.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center">
            <div className="w-20 h-20 rounded-2xl bg-primary-100 flex items-center justify-center mb-6">
              <svg className="w-10 h-10 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-700 mb-2">Waiting for verses...</h3>
            <p className="text-sm text-gray-500 max-w-sm">
              Start speaking to analyze your sermon and retrieve relevant Bible verses automatically.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {verses.map((verse, index) => (
              <VerseDisplay key={`${verse.reference}-${index}`} verse={verse} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default VersesPanel;
