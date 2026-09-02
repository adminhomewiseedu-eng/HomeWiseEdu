import React, { useState, useEffect, useCallback, useRef } from 'react';
import LessonDocView from '../organisms/LessonDocView';
import { curriculumAPI, lessonAPI, voiceAPI, API_BASE_URL } from '../../services/api';
import { speechService } from '../../services/speech';
import { RealtimeClassroom } from '../../services/realtimeClassroom';
import { getLevelLabel } from '../../utils/levels';
import { resolveLessonResume } from '../../utils/lessonResume';
import { adaptiveSilenceMs, isStableBargeCandidate, looksLikeTeacherEcho } from '../../utils/voiceTurn';

export default function LessonPlayerScreen({
  lessonId = 1,
  dayNumber = 1,
  activityType = 'Explore',
  child,
  onExit,
  onProceedToQuiz
}) {
  const [lesson, setLesson] = useState(null);
  const [voiceStatus, setVoiceStatus] = useState('ready'); // ready | connecting | speaking | listening | thinking | reconnecting | paused
  const [isVoicePaused, setIsVoicePaused] = useState(false);
  const [micActive, setMicActive] = useState(false);
  const [lastSpokenText, setLastSpokenText] = useState('');
  const [hasStartedVoice, setHasStartedVoice] = useState(false);
  const [practiceReady, setPracticeReady] = useState(false);
  const [conversationMessages, setConversationMessages] = useState([]);

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
  const openingGraceTimerRef = useRef(null);
  const pendingResumeRef = useRef({ mode: 'new', state: {} });
  const bargeCandidateRef = useRef('');
  const bargeCandidateTimerRef = useRef(null);
  const pendingDeliveryRef = useRef(null);
  const realtimeRef = useRef(null);
  const transcriptHandlerRef = useRef(null);

  const studentName = child?.name || 'Student';
  const eduSys = child?.education_system || 'UK';
  const childLevel = child?.level !== undefined ? child.level : 0;
  const levelLabel = child?.level_label || getLevelLabel(childLevel, eduSys);

  const updateVoiceStatus = useCallback((status) => {
    voiceStatusRef.current = status;
    setVoiceStatus(status);
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
    if (openingGraceTimerRef.current) {
      clearTimeout(openingGraceTimerRef.current);
      openingGraceTimerRef.current = null;
    }
    if (bargeCandidateTimerRef.current) {
      clearTimeout(bargeCandidateTimerRef.current);
      bargeCandidateTimerRef.current = null;
    }
    bargeCandidateRef.current = '';
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

    if (realtimeRef.current?.connected) {
      updateVoiceStatus('listening');
      setMicActive(true);
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
      const pendingSpoken = accumulatedTranscriptRef.current.trim();
      if (!pendingSpoken) return;
      silenceTimerRef.current = setTimeout(() => {
        const finalSpoken = accumulatedTranscriptRef.current.trim();
        if (finalSpoken && isMountedRef.current && !isVoicePausedRef.current && !isProcessingRef.current) {
          listeningSeedRef.current = '';
          stopAllAudioAndMic();
          handleStudentVoiceInput(finalSpoken);
        }
      }, adaptiveSilenceMs(pendingSpoken));
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
      },
      onResult: (transcript) => {
        if (!isMountedRef.current || isVoicePausedRef.current || isProcessingRef.current) return;
        if (transcript && transcript.trim()) {
          if (openingGraceTimerRef.current) {
            clearTimeout(openingGraceTimerRef.current);
            openingGraceTimerRef.current = null;
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
          if (err === 'network') updateVoiceStatus('reconnecting');
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
    if (realtimeRef.current?.connected) return;

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
        if (!spoken) return;
        const interruptMatch = spoken.match(/^(stop|wait|pause|sorry|excuse me|ms ade)\b[,.! ]*(.*)$/i);
        const explicitInterrupt = Boolean(interruptMatch);
        if (!explicitInterrupt && looksLikeTeacherEcho(spoken, currentTutorSpeechRef.current)) return;

        const takeFloor = (capturedSpeech) => {
          if (bargeInTriggeredRef.current) return;
          bargeInTriggeredRef.current = true;
          guidanceRequestRef.current += 1;
          speechService.cancelAllSpeech();
          speechService.stopListening();
          setMicActive(false);
          isProcessingRef.current = false;
          updateVoiceStatus('listening');
          const wordsAfterInterrupt = explicitInterrupt ? (interruptMatch?.[2] || '').trim() : capturedSpeech;
          startContinuousListening(wordsAfterInterrupt);
        };

        if (explicitInterrupt || meta.latestIsFinal) {
          takeFloor(spoken);
          return;
        }

        // A stable interim phrase may take the floor without a wake word. This
        // avoids waiting for Chrome's sometimes-delayed final-result event.
        if (!isStableBargeCandidate(bargeCandidateRef.current, spoken)) {
          bargeCandidateRef.current = spoken;
          return;
        }
        bargeCandidateRef.current = spoken;
        if (bargeCandidateTimerRef.current) clearTimeout(bargeCandidateTimerRef.current);
        bargeCandidateTimerRef.current = setTimeout(() => takeFloor(bargeCandidateRef.current), 500);
      },
      onError: () => {},
      onEnd: () => {
        setMicActive(false);
        if (isMountedRef.current && voiceStatusRef.current === 'speaking' && !bargeInTriggeredRef.current) {
          updateVoiceStatus('reconnecting');
          recognitionRestartTimerRef.current = setTimeout(startBargeInListening, 300);
        }
      }
    });
  }, [startContinuousListening, updateVoiceStatus]);

  // Play audio safely using authoritative single audio controller
  const playTutorVoice = useCallback(async (textToSpeak, afterCurrentPlayback = null) => {
    if (!textToSpeak || !isMountedRef.current) return;

    if (realtimeRef.current?.connected) {
      currentTutorSpeechRef.current = textToSpeak;
      updateVoiceStatus('speaking');
      setLastSpokenText(textToSpeak);
      const completed = await realtimeRef.current.speak(textToSpeak);
      isProcessingRef.current = false;
      if (!isMountedRef.current || isVoicePausedRef.current) return;
      if (completed && afterCurrentPlayback) afterCurrentPlayback();
      else startContinuousListening();
      return;
    }

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
        {
          sender: 'tutor',
          text: tutor_reply,
          speech_text,
          phase: res.data.pedagogical_state?.current_phase || null,
        }
      ];
      historyRef.current = newHistory;
      setConversationMessages(newHistory);

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
        ? () => {
            pendingDeliveryRef.current = delivery_token;
            startContinuousListening();
          }
        : null;
      await playTutorVoice(textToSpeak, afterPlayback);

    } catch (e) {
      console.error('Tutor guidance voice error:', e);
      if (deliveryToken) pendingDeliveryRef.current = deliveryToken;
      isProcessingRef.current = false;
      updateVoiceStatus('listening');
      startContinuousListening();
    }
  }, [child, dayNumber, ensureAudioContext, stopAllAudioAndMic, playTutorVoice, startContinuousListening, updateVoiceStatus]);

  // Student spoken input received from microphone
  const handleStudentVoiceInput = (transcript) => {
    if (!transcript || isVoicePausedRef.current) return;
    const deliveryToken = pendingDeliveryRef.current;
    pendingDeliveryRef.current = null;
    triggerGuidance(
      transcript,
      activeLessonRef.current,
      deliveryToken ? 'teacher_delivery_completed' : null,
      deliveryToken
    );
  };
  transcriptHandlerRef.current = handleStudentVoiceInput;

  // Instant interruption: student clicks microphone orb to speak immediately
  const handleManualInterrupt = () => {
    guidanceRequestRef.current += 1;
    ensureAudioContext();
    stopAllAudioAndMic();
    isProcessingRef.current = false;
    isVoicePausedRef.current = false;
    setIsVoicePaused(false);
    if (realtimeRef.current?.connected) {
      realtimeRef.current.cancelResponse();
      updateVoiceStatus('listening');
      setMicActive(true);
      return;
    }
    startContinuousListening();
  };

  const handleStartClass = async () => {
    if (!lesson || hasStartedVoice) return;
    ensureAudioContext();
    setHasStartedVoice(true);
    isVoicePausedRef.current = false;
    setIsVoicePaused(false);
    updateVoiceStatus('connecting');

    try {
      const tokenResponse = await voiceAPI.createRealtimeSession(child?.id || 1, lesson.id, dayNumber);
      const realtime = new RealtimeClassroom({
        onSpeechStarted: () => {
          if (!isMountedRef.current || isVoicePausedRef.current) return;
          updateVoiceStatus('listening');
          setMicActive(true);
        },
        onSpeechStopped: () => {
          if (isMountedRef.current && !isVoicePausedRef.current) updateVoiceStatus('thinking');
        },
        onTranscript: (text) => transcriptHandlerRef.current?.(text),
        onTutorSpeaking: () => {
          if (isMountedRef.current) updateVoiceStatus('speaking');
        },
        onTutorDone: () => {
          if (isMountedRef.current && !isVoicePausedRef.current) {
            updateVoiceStatus('listening');
            setMicActive(true);
          }
        },
        onConnectionState: (state) => {
          if (state === 'failed' || state === 'disconnected') updateVoiceStatus('reconnecting');
        },
        onError: (message) => console.warn('Realtime classroom:', message),
      });
      await realtime.connect(tokenResponse.data.client_secret);
      if (!isMountedRef.current) {
        realtime.close();
        return;
      }
      realtimeRef.current = realtime;
      updateVoiceStatus('listening');
      setMicActive(true);
    } catch (error) {
      console.warn('Realtime unavailable; using classroom voice fallback.', error);
      realtimeRef.current?.close();
      realtimeRef.current = null;
    }

    const resume = pendingResumeRef.current || { mode: 'new' };
    if (resume.mode === 'complete') {
      updateVoiceStatus('paused');
      realtimeRef.current?.setMuted(true);
      return;
    }
    if (resume.mode === 'active_question') {
      isProcessingRef.current = true;
      playTutorVoice(resume.question);
      return;
    }
    if (resume.mode === 'resume_phase') {
      triggerGuidance(null, lesson, 'resume');
      return;
    }

    // Match the natural reference flow: the student may greet first. If they
    // remain silent, Ms. Ade proactively opens the class after a short grace.
    startContinuousListening();
    openingGraceTimerRef.current = setTimeout(() => {
      openingGraceTimerRef.current = null;
      if (!accumulatedTranscriptRef.current.trim() && !isProcessingRef.current && isMountedRef.current) {
        triggerGuidance(null, lesson);
      }
    }, 4500);
  };

  // Toggle pause/resume voice tutor
  const handleToggleVoicePause = () => {
    if (isVoicePaused) {
      // Resume
      isVoicePausedRef.current = false;
      setIsVoicePaused(false);
      ensureAudioContext();
      realtimeRef.current?.setMuted(false);
      startContinuousListening();
    } else {
      // Pause
      isVoicePausedRef.current = true;
      setIsVoicePaused(true);
      updateVoiceStatus('paused');
      realtimeRef.current?.setMuted(true);
      stopAllAudioAndMic();
    }
  };

  // Initial Mount: Load lesson & start hands-free voice loop
  useEffect(() => {
    const mountCycle = ++mountCycleRef.current;
    isMountedRef.current = true;
    isVoicePausedRef.current = false;
    setHasStartedVoice(false);
    setIsVoicePaused(false);
    pendingDeliveryRef.current = null;
    updateVoiceStatus('connecting');

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
          setConversationMessages(sessionData.messages || []);
          pendingResumeRef.current = resume;
          updateVoiceStatus(resume.mode === 'complete' ? 'paused' : 'ready');
          return;
        } catch (sessionError) {
          console.warn('Lesson session resume unavailable:', sessionError);
        }

        pendingResumeRef.current = { mode: 'new', state: {} };
        updateVoiceStatus('ready');
      } catch (e) {
        console.error('Lesson loading error:', e);
      }
    };

    initLesson();

    return () => {
      isMountedRef.current = false;
      mountCycleRef.current += 1;
      guidanceRequestRef.current += 1;
      pendingDeliveryRef.current = null;
      realtimeRef.current?.close();
      realtimeRef.current = null;
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
            onClick={hasStartedVoice ? handleToggleVoicePause : handleStartClass}
            className={`voice-toggle-pill ${isVoicePaused ? 'paused' : 'active'}`}
            title={!hasStartedVoice ? 'Start the live class' : isVoicePaused ? "Click to resume Ms. Ade's voice tutor" : 'Click to pause voice tutor'}
          >
            {!hasStartedVoice ? '🎙️ Start Class' : isVoicePaused ? '▶️ Resume Voice' : '⏸️ Pause Voice'}
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
            dayNumber={dayNumber}
            activityType={activityType}
            onProceedToQuiz={handleProceedToQuiz}
            practiceReady={practiceReady}
            conversationMessages={conversationMessages}
          />
        </div>
      </div>

      {/* Elegant Floating Voice Tutor Status Bar & Live Radar Orb */}
      <div className={`floating-voice-bar ${voiceStatus}`}>
        <div className="voice-bar-left" onClick={hasStartedVoice ? handleManualInterrupt : handleStartClass} title={hasStartedVoice ? 'Tap to speak with Ms. Ade' : 'Start the live class'}>
          <div className={`voice-avatar-orb ${voiceStatus}`}>
            👩🏾‍🏫
            {voiceStatus === 'speaking' && <span className="ring-pulse green" />}
            {voiceStatus === 'listening' && <span className="ring-pulse blue" />}
            {voiceStatus === 'thinking' && <span className="ring-pulse amber" />}
            {(voiceStatus === 'connecting' || voiceStatus === 'reconnecting') && <span className="ring-pulse amber" />}
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
              {voiceStatus === 'ready' && <span className="status-badge ready">Ready when you are · start the class and say hello</span>}
              {voiceStatus === 'connecting' && <span className="status-badge connecting">Connecting microphone and Ms. Ade…</span>}
              {voiceStatus === 'reconnecting' && <span className="status-badge reconnecting">Reconnecting listening…</span>}
              {voiceStatus === 'paused' && (
                <span className="status-badge paused">
                  ⏸️ Voice tutor paused
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="voice-bar-actions">
          {!hasStartedVoice && voiceStatus !== 'paused' && (
            <button className="voice-action-btn start-class-btn" onClick={handleStartClass}>🎙️ Start Class</button>
          )}
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
