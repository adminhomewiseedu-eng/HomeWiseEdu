import React, { useEffect, useRef } from 'react';

// Format inline markdown: **bold**, *italic*, and newlines → <br/>
function formatMarkdown(text) {
  if (!text) return '';
  const parts = text.split(/(\*\*.+?\*\*)/g);
  const elements = [];
  parts.forEach((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      elements.push(<strong key={`b${i}`}>{part.slice(2, -2)}</strong>);
    } else {
      const lines = part.split('\n');
      lines.forEach((line, j) => {
        if (j > 0) elements.push(<br key={`br${i}-${j}`} />);
        if (line) elements.push(<span key={`t${i}-${j}`}>{line}</span>);
      });
    }
  });
  return elements;
}

export default function TutorChatStream({ messages = [], isGenerating = false, onListenMessage }) {
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isGenerating]);

  return (
    <div className="chat">
      {messages.map((m, idx) => {
        const isMe = m.sender === 'me';
        return (
          <div key={idx} className={`msg ${isMe ? 'me' : ''}`}>
            {!isMe && <div className="mav">👩🏾‍🏫</div>}
            <div className={`mbub ${isMe ? 'me' : 'tutor'}`}>
              <div className="msg-content">{formatMarkdown(m.text)}</div>
              {!isMe && onListenMessage && (
                <button
                  type="button"
                  className="msg-listen-btn"
                  onClick={() => onListenMessage(m.speech_text || m.text)}
                  title="Listen to Ms. Ade speak this"
                >
                  🔊 Listen
                </button>
              )}
            </div>
          </div>
        );
      })}

      {isGenerating && (
        <div className="msg tutor thinking">
          <div className="mav">👩🏾‍🏫</div>
          <div className="mbub tutor">
            <span className="typing-dots" aria-hidden="true">•••</span>
          </div>
        </div>
      )}

      <div ref={chatEndRef} />
    </div>
  );
}
