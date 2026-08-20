import React from 'react';

export default function TutorHeader({ isSpeaking, onStopAudio, studentName = 'Student', status = null }) {
  return (
    <div className="tutor-head">
      <div className={`tutor-av ${isSpeaking ? 'speaking' : ''}`}>
        👩🏾‍🏫
      </div>
      <div style={{ flex: 1 }}>
        <div className="tn">Ms. Ade · Live AI Homeschool Tutor</div>
        <div className="status">
          <div className={`wavebars ${isSpeaking ? 'on' : ''}`}>
            <i></i><i></i><i></i><i></i>
          </div>
          <span>{status || (isSpeaking ? 'Speaking with you…' : 'Listening & Ready')}</span>
        </div>
      </div>
      {isSpeaking && onStopAudio && (
        <button
          className="tutor-stop-btn"
          onClick={onStopAudio}
          title="Pause speech"
        >
          ⏹ Stop
        </button>
      )}
      <div className="pill" style={{ background: '#DBEAFE', color: 'var(--plum)', fontWeight: 800 }}>
        {studentName}
      </div>
    </div>
  );
}
