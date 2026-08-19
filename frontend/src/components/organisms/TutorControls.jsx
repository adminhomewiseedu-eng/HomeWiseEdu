import React from 'react';

export default function TutorControls({ onGotIt, onExplainAgain, onAskQuestion }) {
  return (
    <div className="tutor-controls">
      <button className="gotit" onClick={onGotIt}>
        ✓ I've read this — Got it!
      </button>
      <div className="ctrl-row">
        <button onClick={onExplainAgain}>
          🔄 Explain again
        </button>
        <button onClick={onAskQuestion}>
          🙋 Ask a question
        </button>
      </div>
    </div>
  );
}
