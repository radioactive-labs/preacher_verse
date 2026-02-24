import React from 'react';

function VerseDisplay({ verse }) {
  return (
    <div className="p-6 bg-white border border-gray-200 rounded-xl shadow-sm hover:shadow-md transition-all animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-primary-600 font-semibold text-lg">{verse.reference}</h3>
          {verse.theme && (
            <span className="inline-block mt-2 px-3 py-1 bg-primary-100 text-primary-700 text-xs font-medium rounded-full">
              {verse.theme}
            </span>
          )}
        </div>
        <div className="ml-4">
          <span className="inline-flex items-center px-3 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded-full border border-gray-200">
            {verse.relevance_score}%
          </span>
        </div>
      </div>

      {/* Verse Text */}
      <p className="text-gray-900 text-base leading-relaxed mb-4">
        "{verse.text}"
      </p>

      {/* Why Relevant */}
      {verse.why_relevant && (
        <div className="pt-4 border-t border-gray-200">
          <p className="text-sm text-gray-600 italic">
            {verse.why_relevant}
          </p>
        </div>
      )}

      {/* Timestamp */}
      <div className="mt-4 pt-3 border-t border-gray-100">
        <span className="text-xs text-gray-500">
          {new Date(verse.timestamp).toLocaleTimeString()}
        </span>
      </div>
    </div>
  );
}

export default VerseDisplay;
