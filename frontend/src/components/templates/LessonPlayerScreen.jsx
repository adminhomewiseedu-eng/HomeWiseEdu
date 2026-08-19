import React, { useState, useEffect, useRef, useCallback } from 'react';
import LessonDocView from '../organisms/LessonDocView';
import TutorHeader from '../organisms/TutorHeader';
import TutorChatStream from '../organisms/TutorChatStream';
import TutorControls from '../organisms/TutorControls';
import { curriculumAPI, lessonAPI, voiceAPI, API_BASE_URL } from '../../services/api';
import { speechService } from '../../services/speech';
import { getLevelLabel } from '../../utils/levels';

export default function LessonPlayerScreen({ lessonId = 1, dayNumber = 1, activityType = 'Explore', child, onExit, onProceedToQuiz }) {
  const [lesson, setLesson] = useState(null);
  const [activeTab, setActiveTab] = useState(0);
  const [messages, setMessages] = useState([]);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isLoadingAudio, setIsLoadingAudio] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const audioPlayerRef = useRef(null);

  const studentName = child?.name || 'Student';
  const eduSys = child?.education_system || 'UK';
  const childLevel = child?.level !== undefined ? child.level : 0;
  const levelLabel = child?.level_label || getLevelLabel(childLevel, eduSys);

  // Initialize single welcome message once on mount or when lesson changes
  useEffect(() => {
    let isMounted = true;

    const initLesson = async () => {
      try {
        const res = await curriculumAPI.getLessonDetail(lessonId);
        if (!isMounted) return;
        setLesson(res.data);
        setActiveTab(0);
        
        // Single clean welcome greeting (never auto-generate 5 simultaneous tab explanations)
        setMessages([
          {
            sender: 'tutor',
            text: `Welcome, ${studentName}! I'm Ms. Ade, your AI tutor. Take your time reading through each section, and let me know whenever you need help or have questions! 🌟`
          }
        ]);
      } catch (e) {
        console.warn('Lesson load error:', e);
      }
    };

    initLesson();

    return () => {
      isMounted = false;
      speechService.stop();
      if (audioPlayerRef.current) {
        audioPlayerRef.current.pause();
      }
    };
  }, [lessonId, studentName]);

  const triggerGuidance = useCallback(async (tabIdx, prompt = null, currentLesson = lesson) => {
    if (!currentLesson || isGenerating) return;
    setIsGenerating(true);

    try {
      // If user provided a prompt, display user bubble immediately
      if (prompt) {
        setMessages((prev) => [...prev, { sender: 'me', text: prompt }]);
      }

      const res = await lessonAPI.getChatGuidance(
        child?.id || 1,
        currentLesson.id,
        tabIdx,
        prompt,
        messages
      );

      const { tutor_reply, speech_text } = res.data;
      setMessages((prev) => [
        ...prev,
        { sender: 'tutor', text: tutor_reply, speech_text }
      ]);

      // Save lightweight session
      lessonAPI.updateSession({
        child_id: child?.id || 1,
        lesson_id: currentLesson.id,
        day_number: dayNumber,
        current_tab: tabIdx,
        messages: [...messages, { sender: 'tutor', text: tutor_reply, speech_text }],
        is_completed: false
      }).catch(() => {});

    } catch (e) {
      console.warn('Tutor guidance error:', e);
    } finally {
      setIsGenerating(false);
    }
  }, [lesson, isGenerating, child, messages, dayNumber]);

  const handleListen = async (textToSpeak) => {
    if (!textToSpeak || isSpeaking || isLoadingAudio) return;
    setIsLoadingAudio(true);
    try {
      const res = await voiceAPI.getTTSAudio(textToSpeak);
      if (res.data?.audio_url) {
        const audioSrc = res.data.audio_url.startsWith('http') ? res.data.audio_url : `${API_BASE_URL}${res.data.audio_url}`;
        const audio = new Audio(audioSrc);
        audioPlayerRef.current = audio;
        setIsSpeaking(true);
        audio.onended = () => setIsSpeaking(false);
        audio.onerror = () => {
          setIsSpeaking(false);
          speechService.speak(textToSpeak, () => setIsSpeaking(true), () => setIsSpeaking(false));
        };
        audio.play();
      } else {
        speechService.speak(textToSpeak, () => setIsSpeaking(true), () => setIsSpeaking(false));
      }
    } catch (err) {
      speechService.speak(textToSpeak, () => setIsSpeaking(true), () => setIsSpeaking(false));
    } finally {
      setIsLoadingAudio(false);
    }
  };

  const handleSelectTab = (tabIdx) => {
    setActiveTab(tabIdx);
  };

  const handleGotIt = () => {
    if (activeTab < 4) {
      const next = activeTab + 1;
      setActiveTab(next);
    } else {
      onProceedToQuiz(lesson);
    }
  };

  if (!lesson) {
    return (
      <div style={{ height: '100vh', background: 'var(--plum-deep)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#fff' }}>
        <h2>Loading lesson...</h2>
      </div>
    );
  }

  const latestTutorMsg = messages.filter(m => m.sender === 'tutor').slice(-1)[0];

  return (
    <div className="lesson-screen">
      <div className="lesson-bar">
        <div className="exit" onClick={onExit} style={{ cursor: 'pointer' }}>←</div>
        <div>
          <div className="lb-title">{lesson.title}</div>
          <div className="lb-sub">
            {lesson.unit?.subject?.title || 'Academic Pathway'} · {levelLabel} · Day {dayNumber} ({activityType})
          </div>
        </div>
        <div className="lb-progress">
          <div className="track"><span style={{ width: `${20 + activeTab * 16}%` }} /></div>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {latestTutorMsg && (
            <button 
              onClick={() => handleListen(latestTutorMsg.speech_text || latestTutorMsg.text)}
              disabled={isLoadingAudio || isSpeaking}
              style={{
                background: isSpeaking ? '#22C55E' : 'var(--grape)',
                color: '#fff',
                border: 'none',
                padding: '6px 12px',
                borderRadius: '999px',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}
            >
              {isSpeaking ? '🔊 Speaking...' : isLoadingAudio ? '⏳ Loading...' : '🔊 Listen'}
            </button>
          )}
          <div className="pill" style={{ background: '#F3E8FF', color: 'var(--grape)' }}>
            Day {dayNumber} · {activityType}
          </div>
        </div>
      </div>

      <div className="lesson-body">
        <div className="doc-side">
          <LessonDocView lesson={lesson} activeTab={activeTab} onSelectTab={handleSelectTab} levelLabel={levelLabel} />
        </div>
        <div className="tutor-side">
          <TutorHeader isSpeaking={isSpeaking} studentName={studentName} />
          <TutorChatStream messages={messages} />
          <TutorControls
            onGotIt={handleGotIt}
            onExplainAgain={() => triggerGuidance(activeTab, "Can you explain this section again in a simpler way?")}
            onAskQuestion={() => triggerGuidance(activeTab, "Can you give me an example to help me understand this better?")}
          />
        </div>
      </div>
    </div>
  );
}
