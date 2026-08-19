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
  
  const audioRef = useRef(null);

  const studentName = child?.name || 'Student';
  const eduSys = child?.education_system || 'UK';
  const childLevel = child?.level !== undefined ? child.level : 0;
  const levelLabel = child?.level_label || getLevelLabel(childLevel, eduSys);

  // Stop any currently playing audio or speech synthesis immediately
  const stopAudio = useCallback(() => {
    if (audioRef.current) {
      try {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      } catch (e) {}
    }
    speechService.stop();
    setIsSpeaking(false);
  }, []);

  // Play audio using the attached DOM audio element ref with load() and safe play()
  const playAudioUrl = useCallback((audioUrl, textFallback) => {
    if (!audioUrl && !textFallback) return;

    // Immediately stop previous sound
    stopAudio();

    if (audioUrl && audioRef.current) {
      const fullUrl = audioUrl.startsWith('http') ? audioUrl : `${API_BASE_URL}${audioUrl}`;
      audioRef.current.src = fullUrl;
      audioRef.current.load();
      
      setIsSpeaking(true);
      const playPromise = audioRef.current.play();
      if (playPromise !== undefined) {
        playPromise.catch((err) => {
          console.warn('Autoplay blocked by browser policy, falling back to speech synthesis:', err);
          setIsSpeaking(false);
          if (textFallback) {
            speechService.speak(textFallback, () => setIsSpeaking(true), () => setIsSpeaking(false));
          }
        });
      }
    } else if (textFallback) {
      speechService.speak(textFallback, () => setIsSpeaking(true), () => setIsSpeaking(false));
    }
  }, [stopAudio]);

  // Fetch TTS audio and play it automatically via audioRef
  const handleListen = useCallback(async (textToSpeak) => {
    if (!textToSpeak) return;

    setIsLoadingAudio(true);
    try {
      const res = await voiceAPI.getTTSAudio(textToSpeak);
      if (res.data?.audio_url) {
        playAudioUrl(res.data.audio_url, textToSpeak);
      } else {
        speechService.speak(textToSpeak, () => setIsSpeaking(true), () => setIsSpeaking(false));
      }
    } catch (err) {
      console.warn('TTS API error, falling back to speech synthesis:', err);
      speechService.speak(textToSpeak, () => setIsSpeaking(true), () => setIsSpeaking(false));
    } finally {
      setIsLoadingAudio(false);
    }
  }, [playAudioUrl]);

  // Request guidance on explicit user click/interaction
  const triggerGuidance = useCallback(async (tabIdx, prompt = null, currentLesson = lesson) => {
    if (!currentLesson || isGenerating) return;
    
    // Stop any existing audio immediately when a new question or tab is requested
    stopAudio();
    setIsGenerating(true);

    try {
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

      // Automatically play voice for this new AI response
      const textToRead = speech_text || tutor_reply;
      handleListen(textToRead);

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
  }, [lesson, isGenerating, child, messages, dayNumber, handleListen, stopAudio]);

  // Welcome greeting only on initial mount — decoupled completely from tab changes
  useEffect(() => {
    let isMounted = true;

    const initLesson = async () => {
      try {
        const res = await curriculumAPI.getLessonDetail(lessonId);
        if (!isMounted) return;
        setLesson(res.data);
        setActiveTab(0);

        const welcomeText = `Welcome, ${studentName}! I'm Ms. Ade, your AI tutor for today's lesson on ${res.data.title}. Let's get started! 🌟`;
        setMessages([{ sender: 'tutor', text: welcomeText }]);

        // Auto-play welcome greeting audio
        handleListen(welcomeText);
      } catch (e) {
        console.warn('Lesson load error:', e);
      }
    };

    initLesson();

    return () => {
      isMounted = false;
      stopAudio();
      if (audioRef.current) {
        try {
          audioRef.current.src = '';
        } catch (e) {}
      }
    };
  }, [lessonId, studentName, handleListen, stopAudio]);

  // Explicit user click handler for tabs: stops old audio, sets state AND fetches AI explanation
  const handleSelectTab = (tabIdx) => {
    stopAudio();
    setActiveTab(tabIdx);
    triggerGuidance(tabIdx);
  };

  const handleGotIt = () => {
    stopAudio();
    if (activeTab < 4) {
      const next = activeTab + 1;
      setActiveTab(next);
      triggerGuidance(next);
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
      {/* Hidden audio element with ref for reliable HTML5 DOM audio playback */}
      <audio
        ref={audioRef}
        autoPlay
        onEnded={() => setIsSpeaking(false)}
        onError={() => setIsSpeaking(false)}
        style={{ display: 'none' }}
      />

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
            onExplainAgain={() => {
              stopAudio();
              triggerGuidance(activeTab, "Can you explain this section again in a simpler way?");
            }}
            onAskQuestion={() => {
              stopAudio();
              triggerGuidance(activeTab, "Can you give me an example to help me understand this better?");
            }}
          />
        </div>
      </div>
    </div>
  );
}
