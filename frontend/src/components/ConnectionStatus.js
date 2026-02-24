import React from 'react';
import './ConnectionStatus.css';

function ConnectionStatus({ connected, status, onPing }) {
  return (
    <div className="connection-status">
      <div className={`status-indicator ${connected ? 'connected' : 'disconnected'}`}>
        <span className="status-dot"></span>
        <span className="status-text">{status}</span>
      </div>

      {connected && (
        <button className="ping-button" onClick={onPing}>
          Ping
        </button>
      )}
    </div>
  );
}

export default ConnectionStatus;
