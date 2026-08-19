import React, { useEffect, useRef } from 'react';

export default function TutorChatStream({ messages = [] }) {
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="chat">
      {messages.map((m, idx) => {
        const isMe = m.sender === 'me';
        return (
          <div key={idx} className={`msg ${isMe ? 'me' : ''}`}>
            {!isMe && <div className="mav">👩🏾‍🏫</div>}
            <div className={`mbub ${isMe ? 'me' : 'tutor'}`}>
              {m.text}
            </div>
          </div>
        );
      })}
      <div ref={chatEndRef} />
    </div>
  );
}
