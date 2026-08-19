import React, { useEffect, useRef } from 'react';

// Format inline bold markdown (**text**) into <strong> tags
function formatMarkdown(text) {
  if (!text) return '';
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={i}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

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
              {formatMarkdown(m.text)}
            </div>
          </div>
        );
      })}
      <div ref={chatEndRef} />
    </div>
  );
}
