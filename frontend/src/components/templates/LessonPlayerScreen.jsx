import React, { useState, useEffect, useCallback, useRef } from 'react';
import LessonDocView from '../organisms/LessonDocView';
import { curriculumAPI, lessonAPI, voiceAPI, API_BASE_URL } from '../../services/api';
import { speechService } from '../../services/speech';
import { getLevelLabel } from '../../utils/levels';
import { resolveLessonResume } from '../../utils/lessonResume';

export default function LessonPlayerScreen({
  lessonId = 1,
  dayNumber = 1,
  activityType = 'Explore',
  child,
  onExit,
  onProceedToQuiz
}) {
  const [lesson, setLesson] = useState(null);
  const [voiceStatus, setVoiceStatus] = useState('thinking'); // 'speaking' | 'listening' | 'thinking' | 'paused'
  const [isVoicePaused, setIsVoicePaused] = useState(false);
  const [micActive, setMicActive] = useState(false);
  const [lastSpokenText, setLastSpokenText] = useState('');
  const [hasStartedVoice, setHasStartedVoice] = useState(false);
  const [practiceReady, setPracticeReady] = useState(false);

  // In-memory conversation history (NO UI transcripts rendered to the student)
  const historyRef = useRef([]);
  const audioCtxRef = useRef(null);
  const audioPlayerRef = useRef(null);
  const isMountedRef = useRef(true);
  const isProcessingRef = useRef(false);
  const isVoicePausedRef = useRef(false);
  const recognitionRestartTimerRef = useRef(null);
  const silenceTimerRef = useRef(null);
  const accumulatedTranscriptRef = useRef('');
  const activeLessonRef = useRef(null);
  const guidanceRequestRef = useRef(0);
  const mountCycleRef = useRef(0);

  const studentName = child?.name || 'Student';
  const eduSys = child?.education_system || 'UK';
  const childLevel = child?.level !== undefined ? child.level : 0;
  const levelLabel = child?.level_label || getLevelLabel(childLevel, eduSys);

  // Ensure Web Audio context is initialized/resumed on user gesture
  const ensureAudioContext = useCallback(() => {
    try {
      if (!audioCtxRef.current) {
        audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
      }
      if (audioCtxRef.current.state === 'suspended') {
        audioCtxRef.current.resume().catch(() => {});
      }
    } catch (e) {
      console.warn('AudioContext init note:', e);
    }
  }, []);

  // Halt all audio playback, timers, and microphone listeners immediately
  const stopAllAudioAndMic = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (recognitionRestartTimerRef.current) {
      clearTimeout(recognitionRestartTimerRef.current);
      recognitionRestartTimerRef.current = null;
    }
    accumulatedTranscriptRef.current = '';

    if (audioPlayerRef.current) {
      try {
        audioPlayerRef.current.pause();
        audioPlayerRef.current.currentTime = 0;
      } catch (e) {}
    }
    speechService.stop();
    speechService.stopListening();
    setMicActive(false);
  }, []);

  // Step 2 & 6: Automated Hands-Free Voice Listener Loop with 1.8s Speech Pause Buffer (VAD Debounce)
  const startContinuousListening = useCallback(() => {
    if (!isMountedRef.current || isVoicePausedRef.current || isProcessingRef.current) {
      return;
    }

    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = null;
    }
    if (recognitionRestartTimerRef.current) {
      clearTimeout(recognitionRestartTimerRef.current);
      recognitionRestartTimerRef.current = null;
    }
    accumulatedTranscriptRef.current = '';

    setVoiceStatus('listening');
    setMicActive(true);

    speechService.startListening({
      continuous: true,
      interimResults: true,
      onStart: () => {
        if (!isMountedRef.current || isVoicePausedRef.current) return;
        setVoiceStatus('listening');
        setMicActive(true);
      },
      onResult: (transcript) => {
        if (!isMountedRef.current || isVoicePausedRef.current || isProcessingRef.current) return;
        if (transcript && transcript.trim()) {
          accumulatedTranscriptRef.current = transcript.trim();

          // Reset silence timer: user is speaking or taking a natural breath
          if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
          }

          // VAD Speech Pause Buffer: wait for 1.8 seconds of true silence before finalizing
          silenceTimerRef.current = setTimeout(() => {
            const finalSpoken = accumulatedTranscriptRef.current.trim();
            if (finalSpoken && isMountedRef.current && !isVoicePausedRef.current && !isProcessingRef.current) {
              stopAllAudioAndMic();
              handleStudentVoiceInput(finalSpoken);
            }
          }, 1800);
        }
      },
      onError: (err) => {
        if (!isMountedRef.current || isVoicePausedRef.current || isProcessingRef.current) return;
        // If silence / no-speech and no pending transcript, smoothly restart listening loop
        if ((err === 'no-speech' || err === 'network') && !silenceTimerRef.current) {
          if (recognitionRestartTimerRef.current) clearTimeout(recognitionRestartTimerRef.current);
          recognitionRestartTimerRef.current = setTimeout(() => {
            if (isMountedRef.current && !isVoicePausedRef.current && !isProcessingRef.current && !silenceTimerRef.current) {
              startContinuousListening();
            }
          }, 350);
        }
      },
      onEnd: () => {
        setMicActive(false);
        // If recognition ended naturally without active text processing, loop again
        if (isMountedRef.current && !isVoicePausedRef.current && !isProcessingRef.current) {
          if (!silenceTimerRef.current) {
            if (recognitionRestartTimerRef.current) clearTimeout(recognitionRestartTimerRef.current);
            recognitionRestartTimerRef.current = setTimeout(() => {
              if (isMountedRef.current && !isVoicePausedRef.current && !isProcessingRef.current && !silenceTimerRef.current) {
                startContinuousListening();
              }
            }, 350);
          }
        }
      }
    });
  }, [stopAllAudioAndMic]);

  // Play audio safely using authoritative single audio controller
  const playTutorVoice = useCallback(async (textToSpeak, afterCurrentPlayback = null) => {
    if (!textToSpeak || !isMountedRef.current) return;

    stopAllAudioAndMic();
    setVoiceStatus('speaking');
    setLastSpokenText(textToSpeak);

    const onPlaybackComplete = () => {
      isProcessingRef.current = false;
      if (isMountedRef.current && !isVoicePausedRef.current) {
        if (afterCurrentPlayback) afterCurrentPlayback();
        else startContinuousListening();
      }
    };

    await speechService.playAuthoritativeAudio(
      textToSpeak,
      () => {
        if (isMountedRef.current) setVoiceStatus('speaking');
      },
      onPlaybackComplete
    );
  }, [stopAllAudioAndMic, startContinuousListening]);

  // Request next spoken guidance turn from backend AI Tutor (Ms. Ade)
  const triggerGuidance = useCallback(async (
    userPrompt = null,
    currentLesson = activeLessonRef.current,
    eventType = null,
    deliveryToken = null
  ) => {
    if (!currentLesson || isProcessingRef.current) return;

    ensureAudioContext();
    stopAllAudioAndMic();
    isProcessingRef.current = true;
    const requestId = ++guidanceRequestRef.current;
    setVoiceStatus('thinking');

    try {
      const currentHistory = historyRef.current;
      const updatedHistory = userPrompt
        ? [...currentHistory, { sender: 'me', text: userPrompt }]
        : currentHistory;

      const res = await lessonAPI.getChatGuidance(
        child?.id || 1,
        currentLesson.id,
        dayNumber,
        0,
        userPrompt,
        updatedHistory,
        eventType,
        deliveryToken
      );

      if (!isMountedRef.current || requestId !== guidanceRequestRef.current) return;

      const {
        tutor_reply,
        speech_text,
        practice_ready,
        delivery_token,
        requires_delivery_confirmation
      } = res.data;
      setPracticeReady(practice_ready === true);
      const newHistory = [
        ...updatedHistory,
        { sender: 'tutor', text: tutor_reply, speech_text }
      ];
      historyRef.current = newHistory;

      // Asynchronously record session
      lessonAPI.updateSession({
        child_id: child?.id || 1,
        lesson_id: currentLesson.id,
        day_number: dayNumber,
        current_tab: 0,
        messages: newHistory,
      }).catch(() => {});

      // Speak response out loud
      const textToSpeak = speech_text || tutor_reply;
      const afterPlayback = requires_delivery_confirmation && delivery_token
        ? () => triggerGuidance(null, currentLesson, 'teacher_delivery_completed', delivery_token)
        : null;
      await playTutorVoice(textToSpeak, afterPlayback);

    } catch (e) {
      console.error('Tutor guidance voice error:', e);
      isProcessingRef.current = false;
      setVoiceStatus('listening');
      startContinuousListening();
    }
  }, [child, dayNumber, ensureAudioContext, stopAllAudioAndMic, playTutorVoice, startContinuousListening]);

  // Student spoken input received from microphone
  const handleStudentVoiceInput = (transcript) => {
    if (!transcript || isVoicePausedRef.current) return;
    triggerGuidance(transcript);
  };

  // Instant interruption: student clicks microphone orb to speak immediately
  const handleManualInterrupt = () => {
    guidanceRequestRef.current += 1;
    ensureAudioContext();
    stopAllAudioAndMic();
    isProcessingRef.current = false;
    isVoicePausedRef.current = false;
    setIsVoicePaused(false);
    startContinuousListening();
  };

  // Toggle pause/resume voice tutor
  const handleToggleVoicePause = () => {
    if (isVoicePaused) {
      // Resume
      isVoicePausedRef.current = false;
      setIsVoicePaused(false);
      ensureAudioContext();
      startContinuousListening();
    } else {
      // Pause
      isVoicePausedRef.current = true;
      setIsVoicePaused(true);
      setVoiceStatus('paused');
      stopAllAudioAndMic();
    }
  };

  // Initial Mount: Load lesson & start hands-free voice loop
  useEffect(() => {
    const mountCycle = ++mountCycleRef.current;
    isMountedRef.current = true;
    isVoicePausedRef.current = false;

    const initLesson = async () => {
      try {
        const res = await curriculumAPI.getLessonDetail(lessonId);
        if (!isMountedRef.current || mountCycle !== mountCycleRef.current) return;
        setLesson(res.data);
        activeLessonRef.current = res.data;

        try {
          const sessionRes = await lessonAPI.getSession(child?.id || 1, res.data.id, dayNumber);
          if (!isMountedRef.current || mountCycle !== mountCycleRef.current) return;
          const sessionData = sessionRes.data || {};
          const resume = resolveLessonResume(sessionData);
          setPracticeReady(sessionData.practice_ready === true);
          historyRef.current = sessionData.messages || [];
          setHasStartedVoice(true);

          if (resume.mode !== 'new') {
            if (resume.mode === 'complete') {
              setVoiceStatus('paused');
              return;
            }
            if (resume.mode === 'active_question') {
              isProcessingRef.current = true;
              await playTutorVoice(resume.question);
            } else {
              triggerGuidance(null, res.data, 'resume');
            }
            return;
          }
        } catch (sessionError) {
          console.warn('Lesson session resume unavailable:', sessionError);
        }

        // Genuinely new session: start the proactive greeting once.
        setHasStartedVoice(true);
        triggerGuidance(null, res.data);
      } catch (e) {
        console.error('Lesson loading error:', e);
      }
    };

    initLesson();

    return () => {
      isMountedRef.current = false;
      mountCycleRef.current += 1;
      guidanceRequestRef.current += 1;
      stopAllAudioAndMic();
    };
  }, [lessonId]); // Runs on lesson load

  const handleProceedToQuiz = () => {
    if (!practiceReady) return;
    stopAllAudioAndMic();
    if (onProceedToQuiz && lesson) {
      onProceedToQuiz(lesson);
    }
  };

  if (!lesson) {
    return (
      <div style={{ height: '100vh', background: '#FAF7FD', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--plum)' }}>
        <h2>Loading lesson material...</h2>
      </div>
    );
  }

  return (
    <div className="lesson-screen voice-first-mode">
      {/* Top Bar Navigation */}
      <div className="lesson-bar">
        <div className="exit" onClick={onExit} style={{ cursor: 'pointer' }} title="Back to Dashboard">
          ←
        </div>
        <div>
          <div className="lb-title">{lesson.title}</div>
          <div className="lb-sub">
            {lesson.unit?.subject?.title || 'Academic Pathway'} · {levelLabel} · Day {dayNumber} ({activityType})
          </div>
        </div>

        <div className="lb-progress">
          <div className="track"><span style={{ width: '100%' }} /></div>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            onClick={handleToggleVoicePause}
            className={`voice-toggle-pill ${isVoicePaused ? 'paused' : 'active'}`}
            title={isVoicePaused ? "Click to resume Ms. Ade's voice tutor" : "Click to pause voice tutor"}
          >
            {isVoicePaused ? '▶️ Resume Voice' : '⏸️ Pause Voice'}
          </button>

          <div className="pill" style={{ background: '#F3E8FF', color: 'var(--grape)' }}>
            Day {dayNumber} · {activityType}
          </div>
        </div>
      </div>

      {/* Main Single-Pane Centered Textbook View */}
      <div className="lesson-body-single">
        <div className="doc-viewport">
          <LessonDocView
            lesson={lesson}
            levelLabel={levelLabel}
            onProceedToQuiz={handleProceedToQuiz}
            practiceReady={practiceReady}
          />
        </div>
      </div>

      {/* Elegant Floating Voice Tutor Status Bar & Live Radar Orb */}
      <div className={`floating-voice-bar ${voiceStatus}`}>
        <div className="voice-bar-left" onClick={handleManualInterrupt} title="Tap to interrupt and speak with Ms. Ade">
          <div className={`voice-avatar-orb ${voiceStatus}`}>
            👩🏾‍🏫
            {voiceStatus === 'speaking' && <span className="ring-pulse green" />}
            {voiceStatus === 'listening' && <span className="ring-pulse blue" />}
            {voiceStatus === 'thinking' && <span className="ring-pulse amber" />}
          </div>

          <div className="voice-text-info">
            <div className="voice-title">Ms. Ade · Live Voice Tutor</div>
            <div className="voice-status-msg">
              {voiceStatus === 'speaking' && (
                <span className="status-badge speaking">
                  <span className="live-wave"><i></i><i></i><i></i><i></i></span>
                  Ms. Ade is speaking to you…
                </span>
              )}
              {voiceStatus === 'listening' && (
                <span className="status-badge listening">
                  <span className="mic-dot" />
                  Listening to you… (Speak out loud)
                </span>
              )}
              {voiceStatus === 'thinking' && (
                <span className="status-badge thinking">
                  💭 Thinking of response…
                </span>
              )}
              {voiceStatus === 'paused' && (
                <span className="status-badge paused">
                  ⏸️ Voice tutor paused
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="voice-bar-actions">
          {voiceStatus === 'speaking' && (
            <button
              className="voice-action-btn interrupt-btn"
              onClick={handleManualInterrupt}
              title="Click to interrupt and speak"
            >
              🎤 Interrupt & Speak
            </button>
          )}

          {voiceStatus === 'speaking' && lastSpokenText && (
            <button
              className="voice-action-btn replay-btn"
              onClick={() => {
                ensureAudioContext();
                playTutorVoice(lastSpokenText);
              }}
              title="Replay what Ms. Ade just said"
            >
              🔊 Replay
            </button>
          )}

          <button
            className="voice-action-btn quiz-shortcut-btn"
            onClick={handleProceedToQuiz}
            disabled={!practiceReady}
            title="Start lesson practice quiz"
          >
            {practiceReady ? 'Start Quiz 🏆' : 'Quiz Locked'}
          </button>
        </div>
      </div>
    </div>
  );
}
