import React, { useState } from 'react';
import { speechService } from '../../services/speech';

export default function TutorControls({
  onSendMessage,
  onProceedToQuiz,
  onInterrupt,
  isGenerating = false,
  isSpeaking = false
}) {
  const [inputText, setInputText] = useState('');
  const [isRecording, setIsRecording] = useState(false);

  const handleSend = (e) => {
    e?.preventDefault();
    if (!inputText.trim() || isGenerating) return;
    if (onInterrupt) onInterrupt();
    onSendMessage(inputText.trim());
    setInputText('');
  };

  const handleMicToggle = () => {
    // 0ms instant interruption: halt Ms. Ade's audio immediately
    if (onInterrupt) onInterrupt();

    if (isRecording) {
      speechService.stopListening();
      setIsRecording(false);
      return;
    }

    if (!speechService.isRecognitionSupported()) {
      alert('Speech recognition is not supported in this browser. You can type your message!');
      return;
    }

    speechService.startListening({
      onStart: () => {
        setIsRecording(true);
        if (onInterrupt) onInterrupt();
      },
      onResult: (transcript) => {
        setIsRecording(false);
        if (transcript && transcript.trim()) {
          onSendMessage(transcript.trim());
        }
      },
      onError: (err) => {
        console.warn('Speech recognition error:', err);
        setIsRecording(false);
      },
      onEnd: () => setIsRecording(false),
    });
  };

  const QUICK_PROMPTS = [
    "Can you give me a fun example?",
    "Explain this in a simpler way",
    "I understand! What's next?",
    "I have a question about this"
  ];

  return (
    <div className="tutor-controls-box">
      {/* Quick Interactive Suggestion Chips */}
      <div className="quick-chips">
        {QUICK_PROMPTS.map((prompt, idx) => (
          <button
            key={idx}
            className="chip-btn"
            disabled={isGenerating}
            onClick={() => {
              if (onInterrupt) onInterrupt();
              onSendMessage(prompt);
            }}
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* Voice & Text Input Row */}
      <form className="tutor-input-row" onSubmit={handleSend}>
        <button
          type="button"
          className={`mic-btn ${isRecording ? 'recording' : ''}`}
          onClick={handleMicToggle}
          title={isRecording ? "Listening to your voice... (click to stop)" : "Click to speak with Ms. Ade (interrupts speech)"}
        >
          {isRecording ? '🔴 Listening...' : '🎤 Speak'}
        </button>

        <input
          type="text"
          className="tutor-text-input"
          placeholder={isRecording ? "Listening to your voice..." : "Speak or type your answer to Ms. Ade..."}
          value={inputText}
          onChange={(e) => {
            setInputText(e.target.value);
            if (isSpeaking && onInterrupt) onInterrupt();
          }}
          disabled={isGenerating}
        />

        <button
          type="submit"
          className="send-btn"
          disabled={!inputText.trim() || isGenerating}
        >
          Send ➔
        </button>
      </form>

      {/* Main Lesson Progression Action */}
      <button className="quiz-ready-btn" onClick={onProceedToQuiz}>
        ✓ I've Read & Discussed This — Start Practice Quiz! 🏆
      </button>
    </div>
  );
}
