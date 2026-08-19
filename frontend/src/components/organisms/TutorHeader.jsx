import React from 'react';

export default function TutorHeader({ isSpeaking, studentName = 'James', status = null }) {
  return (
    <div className="tutor-head">
      <div className={`tutor-av ${isSpeaking ? 'speaking' : ''}`}>
        👩🏾‍🏫
      </div>
      <div style={{ flex: 1 }}>
        <div className="tn">Ms. Ade</div>
        <div className="status">
          <div className={`wavebars ${isSpeaking ? 'on' : ''}`}>
            <i></i><i></i><i></i><i></i>
          </div>
          <span>{status || (isSpeaking ? 'Teaching…' : 'Listening')}</span>
        </div>
      </div>
      <div className="pill" style={{ background: '#DBEAFE', color: 'var(--plum)' }}>
        {studentName}
      </div>
    </div>
  );
}
