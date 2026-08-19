import React, { useState, useEffect, useCallback } from 'react';
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

  const studentName = child?.name || 'Student';
  const eduSys = child?.education_system || 'UK';
  const childLevel = child?.level !== undefined ? child.level : 0;
  const levelLabel = child?.level_label || getLevelLabel(childLevel, eduSys);

  // Stop any currently playing audio immediately
  const stopAudio = useCallback(() => {
    const player = document.getElementById('lesson-audio-player');
    if (player) {
      try {
        player.pause();
        player.currentTime = 0;
        player.src = '';
      } catch (e) {}
    }
    speechService.stop();
    setIsSpeaking(false);
  }, []);

  // Directly play audio URL through the persistent DOM audio element
  const playAudioDirect = useCallback((newAudioUrl, textFallback) => {
    stopAudio();

    if (newAudioUrl) {
      const player = document.getElementById('lesson-audio-player');
      if (player) {
        const fullUrl = newAudioUrl.startsWith('http') ? newAudioUrl : `${API_BASE_URL}${newAudioUrl}`;
        player.src = fullUrl;
        player.load();
        setIsSpeaking(true);
        player.play().catch((err) => {
          console.error('Autoplay blocked:', err);
          setIsSpeaking(false);
          if (textFallback) {
            speechService.speak(textFallback, () => setIsSpeaking(true), () => setIsSpeaking(false));
          }
        });
        return;
      }
    }

    if (textFallback) {
      speechService.speak(textFallback, () => setIsSpeaking(true), () => setIsSpeaking(false));
    }
  }, [stopAudio]);

  // Fetch TTS audio and play it directly
  const handleListen = useCallback(async (textToSpeak) => {
    if (!textToSpeak) return;

    setIsLoadingAudio(true);
    try {
      const res = await voiceAPI.getTTSAudio(textToSpeak);
      if (res.data?.audio_url) {
        playAudioDirect(res.data.audio_url, textToSpeak);
      } else {
        speechService.speak(textToSpeak, () => setIsSpeaking(true), () => setIsSpeaking(false));
      }
    } catch (err) {
      console.error('TTS API error, falling back to speech synthesis:', err);
      speechService.speak(textToSpeak, () => setIsSpeaking(true), () => setIsSpeaking(false));
    } finally {
      setIsLoadingAudio(false);
    }
  }, [playAudioDirect]);

  // Request AI guidance when user clicks tab or asks question
  const triggerGuidance = useCallback(async (tabIdx, prompt = null, currentLesson = lesson) => {
    if (!currentLesson || isGenerating) return;

    // 1. Instantly stop old audio
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

      // 2. Play audio directly inside the resolving block
      const textToRead = speech_text || tutor_reply;
      handleListen(textToRead);

      // 3. Save lightweight session
      lessonAPI.updateSession({
        child_id: child?.id || 1,
        lesson_id: currentLesson.id,
        day_number: dayNumber,
        current_tab: tabIdx,
        messages: [...messages, { sender: 'tutor', text: tutor_reply, speech_text }],
        is_completed: false
      }).catch(() => {});

    } catch (e) {
      console.error('Tutor guidance error:', e);
    } finally {
      setIsGenerating(false);
    }
  }, [lesson, isGenerating, child, messages, dayNumber, handleListen, stopAudio]);

  // Initial mount: load lesson and fire welcome greeting
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

        // Directly play welcome audio
        handleListen(welcomeText);
      } catch (e) {
        console.error('Lesson load error:', e);
      }
    };

    initLesson();

    return () => {
      isMounted = false;
      stopAudio();
    };
  }, [lessonId, studentName, handleListen, stopAudio]);

  // Tab click: instantly stop audio, update tab, trigger guidance
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
      {/* DOM audio player for single-source reliable playback */}
      <audio
        id="lesson-audio-player"
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
