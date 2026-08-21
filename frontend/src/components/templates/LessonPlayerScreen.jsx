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
  const voiceStatusRef = useRef('thinking');
  const currentTutorSpeechRef = useRef('');
  const bargeInTriggeredRef = useRef(false);
  const tutorPlaybackStartedAtRef = useRef(0);
  const listeningSeedRef = useRef('');
  const awaitingBargeSpeechRef = useRef(false);
  const bargeNoSpeechTimerRef = useRef(null);

  const studentName = child?.name || 'Student';
  const eduSys = child?.education_system || 'UK';
  const childLevel = child?.level !== undefined ? child.level : 0;
  const levelLabel = child?.level_label || getLevelLabel(childLevel, eduSys);

  const updateVoiceStatus = useCallback((status) => {
    voiceStatusRef.current = status;
    setVoiceStatus(status);
  }, []);

  const normalizedWords = (text) => new Set(
    String(text || '').toLowerCase().replace(/[^a-z0-9' ]/g, ' ').split(/\s+/).filter((word) => word.length > 2)
  );

  const looksLikeTeacherEcho = useCallback((transcript) => {
    const normalizedHeard = String(transcript || '').toLowerCase().replace(/[^a-z0-9' ]/g, ' ').replace(/\s+/g, ' ').trim();
    const normalizedTeacher = String(currentTutorSpeechRef.current || '').toLowerCase().replace(/[^a-z0-9' ]/g, ' ').replace(/\s+/g, ' ').trim();
    if (!normalizedHeard) return true;
    if (normalizedTeacher.includes(normalizedHeard)) return true;

    const heard = [...normalizedWords(normalizedHeard)];
    if (!heard.length) return true;
    const teacher = normalizedWords(normalizedTeacher);
    const overlap = heard.filter((word) => teacher.has(word)).length / heard.length;
    return overlap >= 0.5;
  }, []);

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
    if (bargeNoSpeechTimerRef.current) {
      clearTimeout(bargeNoSpeechTimerRef.current);
      bargeNoSpeechTimerRef.current = null;
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
  const startContinuousListening = useCallback((initialTranscript = '') => {
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
    listeningSeedRef.current = initialTranscript.trim();
    accumulatedTranscriptRef.current = listeningSeedRef.current;

    const finalizeAfterPause = () => {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      silenceTimerRef.current = setTimeout(() => {
        const finalSpoken = accumulatedTranscriptRef.current.trim();
        if (finalSpoken && isMountedRef.current && !isVoicePausedRef.current && !isProcessingRef.current) {
          listeningSeedRef.current = '';
          stopAllAudioAndMic();
          handleStudentVoiceInput(finalSpoken);
        }
      }, 1800);
    };

    updateVoiceStatus('listening');
    setMicActive(true);

    speechService.startListening({
      continuous: true,
      interimResults: true,
      onStart: () => {
        if (!isMountedRef.current || isVoicePausedRef.current) return;
        updateVoiceStatus('listening');
        setMicActive(true);
        if (listeningSeedRef.current) finalizeAfterPause();
        if (awaitingBargeSpeechRef.current && !listeningSeedRef.current) {
          bargeNoSpeechTimerRef.current = setTimeout(() => {
            if (!accumulatedTranscriptRef.current.trim() && isMountedRef.current && !isProcessingRef.current) {
              awaitingBargeSpeechRef.current = false;
              playTutorVoice("Did you want to say something? I'm listening.");
            }
          }, 3500);
        }
      },
      onResult: (transcript) => {
        if (!isMountedRef.current || isVoicePausedRef.current || isProcessingRef.current) return;
        if (transcript && transcript.trim()) {
          awaitingBargeSpeechRef.current = false;
          if (bargeNoSpeechTimerRef.current) {
            clearTimeout(bargeNoSpeechTimerRef.current);
            bargeNoSpeechTimerRef.current = null;
          }
          accumulatedTranscriptRef.current = [listeningSeedRef.current, transcript.trim()].filter(Boolean).join(' ');
          // Wait through natural pauses so a child's full thought is captured.
          finalizeAfterPause();
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
  }, [stopAllAudioAndMic, updateVoiceStatus]);

  // Keep recognition open during teacher playback so clear student speech can
  // interrupt naturally. Echo-like transcripts are ignored so Ms. Ade does not
  // interrupt herself through the speakers.
  const startBargeInListening = useCallback(() => {
    if (!isMountedRef.current || isVoicePausedRef.current || bargeInTriggeredRef.current) return;

    speechService.startListening({
      continuous: true,
      interimResults: true,
      onStart: () => setMicActive(true),
      onResult: (transcript, meta = {}) => {
        if (!isMountedRef.current || isVoicePausedRef.current || bargeInTriggeredRef.current) return;
        // Briefly ignore startup leakage from the newly-started speaker, but do
        // not impose a noticeable wake-word window on the student.
        if (Date.now() - tutorPlaybackStartedAtRef.current < 500) return;
        const spoken = (meta.latestTranscript || transcript).trim();
        if (!spoken || looksLikeTeacherEcho(spoken)) return;

        const interruptMatch = spoken.match(/^(stop|wait|pause|sorry|excuse me|ms ade)\b[,.! ]*(.*)$/i);
        const explicitInterrupt = Boolean(interruptMatch);
        // Explicit barge-in words pause immediately even while recognition is
        // interim. Other speech must first be finalized to avoid speaker echo.
        if (!explicitInterrupt && !meta.latestIsFinal) return;

        bargeInTriggeredRef.current = true;
        guidanceRequestRef.current += 1;
        speechService.cancelAllSpeech();
        speechService.stopListening();
        setMicActive(false);
        isProcessingRef.current = false;
        updateVoiceStatus('listening');

        // "Wait" is a floor-taking signal, not the student's complete answer.
        // Preserve only words spoken after it, then wait for the full utterance.
        const wordsAfterInterrupt = explicitInterrupt ? (interruptMatch?.[2] || '').trim() : spoken;
        awaitingBargeSpeechRef.current = !wordsAfterInterrupt;
        startContinuousListening(wordsAfterInterrupt);
      },
      onError: () => {},
      onEnd: () => {
        setMicActive(false);
        if (isMountedRef.current && voiceStatusRef.current === 'speaking' && !bargeInTriggeredRef.current) {
          recognitionRestartTimerRef.current = setTimeout(startBargeInListening, 250);
        }
      }
    });
  }, [looksLikeTeacherEcho, startContinuousListening, updateVoiceStatus]);

  // Play audio safely using authoritative single audio controller
  const playTutorVoice = useCallback(async (textToSpeak, afterCurrentPlayback = null) => {
    if (!textToSpeak || !isMountedRef.current) return;

    stopAllAudioAndMic();
    bargeInTriggeredRef.current = false;
    currentTutorSpeechRef.current = textToSpeak;
    updateVoiceStatus('speaking');
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
        if (isMountedRef.current) {
          tutorPlaybackStartedAtRef.current = Date.now();
          updateVoiceStatus('speaking');
          startBargeInListening();
        }
      },
      onPlaybackComplete
    );
  }, [stopAllAudioAndMic, startContinuousListening, startBargeInListening, updateVoiceStatus]);

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
    updateVoiceStatus('thinking');

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
      updateVoiceStatus('listening');
      startContinuousListening();
    }
  }, [child, dayNumber, ensureAudioContext, stopAllAudioAndMic, playTutorVoice, startContinuousListening, updateVoiceStatus]);

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
      updateVoiceStatus('paused');
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
              updateVoiceStatus('paused');
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
                  Ms. Ade is speaking · microphone open for interruption…
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
              title="Optional backup if hands-free interruption is not detected"
            >
              🎤 Tap if needed
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
