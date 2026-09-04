import React from 'react';

export default function TutorHeader({ isSpeaking, onStopAudio, studentName = 'Student' }) {
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
