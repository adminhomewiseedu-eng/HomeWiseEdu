import React, { useState, useEffect, useCallback, useRef } from 'react';
import LessonDocView from '../organisms/LessonDocView';
import { curriculumAPI, lessonAPI, voiceAPI, API_BASE_URL } from '../../services/api';
import { speechService } from '../../services/speech';
import { RealtimeClassroom } from '../../services/realtimeClassroom';
import { getLevelLabel } from '../../utils/levels';
import { resolveLessonResume } from '../../utils/lessonResume';
import { adaptiveSilenceMs, isStableBargeCandidate, looksLikeTeacherEcho } from '../../utils/voiceTurn';
import { teacherDeliveryLooksComplete } from '../../utils/teacherDelivery';
import {
  nextAuthoritativeRealtimeTurn,
  shouldAcknowledgeTeacherDelivery,
  isCurrentAuthoritativeResponse,
} from '../../utils/realtimeProgression';
import { deferRealtimeCompletion, drainRealtimeCompletion } from '../../utils/realtimeCompletionQueue';
import { RealtimeRequestLedger } from '../../utils/realtimeRequestLedger';
import BrandLogo from '../molecules/BrandLogo';

const realtimeTraceEnabled = () => {
  try { return new URLSearchParams(window.location.search).get('realtimeTrace') === '1'; } catch (_) { return false; }
};
const traceRealtimeAuthority = (event, details = {}) => {
  if (realtimeTraceEnabled()) console.info('[HWE Authority]', { event, ...details });
};

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
  const realtimeBaseInstructionsRef = useRef('');
  const realtimeStateRef = useRef({});
  const realtimeDeliveryTokenRef = useRef(null);
  const lastRealtimeStudentTranscriptRef = useRef('');
  const realtimeEventInFlightRef = useRef(false);
  const pendingRealtimeTutorDoneRef = useRef(null);
  const realtimePhaseInstructionRef = useRef('');
  const realtimeRequestedTurnRef = useRef(new RealtimeRequestLedger());
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

  const applyRealtimeAuthority = useCallback((data, realtime = realtimeRef.current) => {
    if (!data) return;
    const state = data.pedagogical_state || {};
    realtimeStateRef.current = state;
    realtimeDeliveryTokenRef.current = data.delivery_token || null;
    realtimePhaseInstructionRef.current = data.phase_instruction || '';
    setPracticeReady(data.practice_ready === true);
    traceRealtimeAuthority('backend.state', {
      phase: state.current_phase || null,
      workedExamplesDelivered: state.worked_examples_delivered || null,
      awaitingStudent: Boolean(state.active_question && state.active_phase === state.current_phase),
      teacherLed: ['GREETING', 'TEACHING', 'WORKED_EXAMPLE_1', 'WORKED_EXAMPLE_2', 'WORKED_EXAMPLE_3', 'LESSON_SUMMARY'].includes(state.current_phase),
      hasDeliveryToken: Boolean(data.delivery_token),
    });
    if (realtime?.connected) {
      realtime.updateInstructions(
        `${realtimeBaseInstructionsRef.current}\nCURRENT_AUTHORITATIVE_STATE=${JSON.stringify(state)}\n${data.phase_instruction || ''}`
      );
    }
  }, []);

  const continueFromAuthority = useCallback((previousPhase, data, realtime = realtimeRef.current) => {
    const nextTurn = nextAuthoritativeRealtimeTurn(previousPhase, data?.pedagogical_state);
    if (!nextTurn || !realtime?.connected) return false;
    const requestKey = `${previousPhase || 'RECOVERY'}->${nextTurn.phase}:${nextTurn.tag}`;
    const metadata = realtimeRequestedTurnRef.current.reserve({
      requestKey,
      responseTag: nextTurn.tag,
      authoritativePhase: nextTurn.phase,
      deliveryToken: nextTurn.tag === 'teacher_delivery' ? (data.delivery_token || null) : null,
    });
    if (!metadata) {
      traceRealtimeAuthority('request_key.blocked', { requestKey, phase: nextTurn.phase });
      return false;
    }
    traceRealtimeAuthority('request_key.acquired', { requestKey, phase: nextTurn.phase, hasDeliveryToken: Boolean(metadata.deliveryToken) });
    const requested = realtime.createResponse(data.phase_instruction, nextTurn.tag, metadata);
    if (!requested) {
      realtimeRequestedTurnRef.current.release(requestKey);
      traceRealtimeAuthority('request_key.released', { requestKey, reason: 'create_failed' });
    }
    return requested;
  }, []);

  const requestCurrentTeacherTurn = useCallback((instructions, previousPhase, realtime = realtimeRef.current) => {
    const phase = realtimeStateRef.current?.current_phase || null;
    const token = realtimeDeliveryTokenRef.current || null;
    if (!phase || !token || !realtime?.connected) return false;
    const requestKey = `${previousPhase || phase}->${phase}:teacher_delivery`;
    const metadata = realtimeRequestedTurnRef.current.reserve({
      requestKey,
      responseTag: 'teacher_delivery',
      authoritativePhase: phase,
      deliveryToken: token,
    });
    if (!metadata) return false;
    traceRealtimeAuthority('request_key.acquired', { requestKey, phase, hasDeliveryToken: true });
    const requested = realtime.createResponse(instructions, 'teacher_delivery', metadata);
    if (!requested) {
      realtimeRequestedTurnRef.current.release(requestKey);
      traceRealtimeAuthority('request_key.released', { requestKey, reason: 'create_failed' });
    }
    return requested;
  }, []);

  const postRealtimeEvent = useCallback(async (event) => {
    const response = await lessonAPI.sendRealtimePedagogyEvent({
      child_id: child?.id || 1,
      lesson_id: activeLessonRef.current?.id || lessonId,
      day_number: dayNumber,
      ...event,
    });
    return response.data;
  }, [child, lessonId, dayNumber]);

  const realtimeResponseTag = (state, fallback = 'academic_prompt') => (
    ['GREETING', 'TEACHING', 'WORKED_EXAMPLE_1', 'WORKED_EXAMPLE_2', 'WORKED_EXAMPLE_3', 'LESSON_SUMMARY']
      .includes(state?.current_phase) ? 'teacher_delivery' : fallback
  );

  const handleStartClass = async () => {
    if (!lesson || hasStartedVoice) return;
    // Invalidate late REST/TTS work and silence every provider before opening
    // the single authoritative Realtime voice.
    guidanceRequestRef.current += 1;
    realtimeRef.current?.close();
    realtimeRef.current = null;
    realtimeRequestedTurnRef.current.clear();
    stopAllAudioAndMic();
    ensureAudioContext();
    setHasStartedVoice(true);
    isVoicePausedRef.current = false;
    setIsVoicePaused(false);
    updateVoiceStatus('connecting');

    let realtimeStarted = false;
    try {
      const tokenResponse = await voiceAPI.createRealtimeSession(child?.id || 1, lesson.id, dayNumber);
      realtimeBaseInstructionsRef.current = tokenResponse.data.base_instructions || '';
      realtimeStateRef.current = tokenResponse.data.pedagogical_state || {};
      let realtime;
      realtime = new RealtimeClassroom({
        onSpeechStarted: () => {
          if (!isMountedRef.current || isVoicePausedRef.current) return;
          updateVoiceStatus('listening');
          setMicActive(true);
        },
        onSpeechStopped: () => {
          if (isMountedRef.current && !isVoicePausedRef.current) updateVoiceStatus('thinking');
        },
        onTranscript: (text) => {
          lastRealtimeStudentTranscriptRef.current = text;
        },
        onTutorSpeaking: () => {
          if (isMountedRef.current) updateVoiceStatus('speaking');
        },
        onResponseInterrupted: (metadata) => {
          realtimeRequestedTurnRef.current.release(metadata?.requestKey);
          traceRealtimeAuthority('request_key.released', { requestKey: metadata?.requestKey || null, reason: 'interrupted' });
        },
        onResponseFailed: (metadata) => {
          realtimeRequestedTurnRef.current.release(metadata?.requestKey);
          traceRealtimeAuthority('request_key.released', { requestKey: metadata?.requestKey || null, reason: 'response_failed' });
          if (metadata?.deliveryToken === realtimeDeliveryTokenRef.current
            && metadata?.authoritativePhase === realtimeStateRef.current?.current_phase) {
            requestCurrentTeacherTurn(
              realtimePhaseInstructionRef.current,
              metadata.authoritativePhase,
              realtime,
            );
          }
        },
        onToolCall: async ({ name, callId, arguments: rawArguments }) => {
          if (name !== 'submit_academic_response') return;
          const authoritativePhase = realtimeStateRef.current?.current_phase;
          const academicPhases = ['UNDERSTANDING_CHECK', 'GUIDED_PRACTICE', 'APPLICATION', 'MASTERY_CHECK'];
          if (!academicPhases.includes(authoritativePhase)) {
            realtime.sendFunctionOutput(callId, {
              accepted_as_academic_evidence: false,
              authoritative_phase: authoritativePhase,
              instruction: 'This is a teacher-led phase. Respond naturally without evaluating mastery or mentioning submission.',
            }, (
              'The learner was heard clearly. This is still a teacher-led phase, so do not submit or evaluate the '
              + 'answer. Briefly acknowledge what the learner said, continue the current authoritative teaching '
              + 'phase, and never mention a tool, submission, technical problem, or failure.'
            ), realtimeResponseTag(realtimeStateRef.current, 'teacher_conversation'));
            lastRealtimeStudentTranscriptRef.current = '';
            return;
          }
          if (realtimeEventInFlightRef.current) {
            realtime.sendFunctionOutput(callId, {
              error: 'Authoritative validation is already in progress. Do not evaluate or advance.',
            }, 'Briefly ask the learner to wait a moment. Do not mention a tool, submission, or technical failure.');
            return;
          }
          realtimeEventInFlightRef.current = true;
          try {
            const args = JSON.parse(rawArguments || '{}');
            const studentResponse = String(args.student_response || lastRealtimeStudentTranscriptRef.current || '').trim();
            const data = await postRealtimeEvent({
              event_type: 'academic_response',
              student_response: studentResponse,
            });
            applyRealtimeAuthority(data, realtime);
            realtime.sendFunctionOutput(callId, {
              authoritative_state: data.pedagogical_state,
              evaluation: data.evaluation,
              instruction: data.phase_instruction,
            }, data.phase_instruction, realtimeResponseTag(data.pedagogical_state, 'academic_feedback'));
            lastRealtimeStudentTranscriptRef.current = '';
          } catch (error) {
            console.warn('Realtime academic tool failed safely:', error);
            realtime.sendFunctionOutput(callId, {
              error: 'Academic validation was unavailable. Do not advance or grant mastery. Ask the learner to try again.',
            }, 'Backend validation failed. Do not advance. Briefly ask the learner to try the same question again.');
          } finally {
            realtimeEventInFlightRef.current = false;
            drainRealtimeCompletion(
              pendingRealtimeTutorDoneRef,
              isMountedRef.current && realtime.connected,
              (pendingCompletion) => realtime.handlers.onTutorDone?.(pendingCompletion),
            );
          }
        },
        onTutorDone: async ({ completed, transcript, hadAudio, responseTag, responseMetadata }) => {
          if (!isMountedRef.current || isVoicePausedRef.current) return;
          updateVoiceStatus('listening');
          setMicActive(true);
          const requestKey = responseMetadata?.requestKey || null;
          if (!completed || !hadAudio) {
            realtimeRequestedTurnRef.current.release(requestKey);
            traceRealtimeAuthority('request_key.released', { requestKey, reason: completed ? 'no_audio' : 'not_completed' });
            if (responseMetadata?.deliveryToken === realtimeDeliveryTokenRef.current
              && responseMetadata?.authoritativePhase === realtimeStateRef.current?.current_phase) {
              requestCurrentTeacherTurn(
                realtimePhaseInstructionRef.current,
                responseMetadata.authoritativePhase,
                realtime,
              );
            }
            return;
          }
          if (realtimeEventInFlightRef.current) {
            deferRealtimeCompletion(
              pendingRealtimeTutorDoneRef,
              { completed, transcript, hadAudio, responseTag, responseMetadata },
            );
            return;
          }
          const completedPhase = responseMetadata?.authoritativePhase
            || realtimeStateRef.current?.current_phase
            || null;
          if (transcript) {
            setLastSpokenText(transcript);
            setConversationMessages((messages) => [
              ...messages,
              { sender: 'tutor', text: transcript, speech_text: transcript, phase: completedPhase },
            ]);
          }
          if (responseTag === 'lesson_complete') {
            updateVoiceStatus('paused');
            setMicActive(false);
            setIsVoicePaused(true);
            isVoicePausedRef.current = true;
            realtime.close();
            realtimeRef.current = null;
            setHasStartedVoice(false);
            return;
          }
          realtimeEventInFlightRef.current = true;
          try {
            const teacherDeliveryPhases = ['GREETING', 'TEACHING', 'WORKED_EXAMPLE_1', 'WORKED_EXAMPLE_2', 'WORKED_EXAMPLE_3', 'LESSON_SUMMARY'];
            const academicPhases = ['UNDERSTANDING_CHECK', 'GUIDED_PRACTICE', 'APPLICATION', 'MASTERY_CHECK'];
            const isAuthoritativeTeacherDelivery = responseTag === 'teacher_delivery'
              && teacherDeliveryPhases.includes(completedPhase)
              && Boolean(responseMetadata?.deliveryToken)
              && Boolean(requestKey);
            if (isAuthoritativeTeacherDelivery && !isCurrentAuthoritativeResponse(
              responseMetadata,
              realtimeStateRef.current,
              realtimeDeliveryTokenRef.current,
            )) {
              realtimeRequestedTurnRef.current.release(requestKey);
              requestCurrentTeacherTurn(
                realtimePhaseInstructionRef.current,
                realtimeStateRef.current?.current_phase,
                realtime,
              );
              return;
            }
            const transcriptComplete = teacherDeliveryLooksComplete(completedPhase, transcript);
            const authorityWaitingForTeacher = teacherDeliveryPhases.includes(realtimeStateRef.current?.current_phase)
              && Boolean(realtimeDeliveryTokenRef.current);
            if (!isAuthoritativeTeacherDelivery && authorityWaitingForTeacher) {
              // Automatic Realtime replies to an interruption, acknowledgement,
              // or help request are conversational. They must never consume the
              // server-issued delivery token. Resume the same teacher phase in
              // a separately tagged response after addressing the learner.
              lastRealtimeStudentTranscriptRef.current = '';
              requestCurrentTeacherTurn(
                `${realtimePhaseInstructionRef.current}\nThe learner has just spoken during this teacher-led phase. Respond directly to what they said, help or clarify if requested, then resume and fully deliver the current phase from the interrupted point. Do not count their acknowledgement as completion.`,
                realtimeStateRef.current?.current_phase,
                realtime,
              );
              return;
            }
            if (isAuthoritativeTeacherDelivery && !shouldAcknowledgeTeacherDelivery(
              responseTag,
              completed,
              hadAudio,
              transcriptComplete,
            )) {
              realtimeRequestedTurnRef.current.release(requestKey);
              requestCurrentTeacherTurn(
                `${realtimePhaseInstructionRef.current}\nYour previous turn was only an acknowledgement or ended before the required phase content and direct question. Continue the same phase now. Do not repeat the acknowledgement and do not ask whether the learner is ready.`,
                completedPhase,
                realtime,
              );
              return;
            }
            if (academicPhases.includes(completedPhase)
              && responseTag === 'academic_feedback'
              && !teacherDeliveryLooksComplete(completedPhase, transcript)) {
              realtime.createResponse(
                `${realtimePhaseInstructionRef.current}\nYour previous response ended with a transition but did not deliver the current academic question or task. Ask the required concrete question now. Never stop after saying that you will move to the next step.`,
                'academic_feedback',
              );
              return;
            }
            const unsubmittedStudentResponse = String(lastRealtimeStudentTranscriptRef.current || '').trim();
            if (academicPhases.includes(completedPhase)
              && responseTag !== 'academic_feedback'
              && unsubmittedStudentResponse) {
              // Realtime occasionally speaks a generic acknowledgement instead
              // of invoking the required academic tool. Fail closed through the
              // backend and immediately continue from its authoritative result.
              const data = await postRealtimeEvent({
                event_type: 'academic_response',
                student_response: unsubmittedStudentResponse,
              });
              applyRealtimeAuthority(data, realtime);
              lastRealtimeStudentTranscriptRef.current = '';
              realtime.createResponse(
                data.phase_instruction,
                realtimeResponseTag(data.pedagogical_state, 'academic_feedback'),
              );
              return;
            }
            const deliveryToken = isAuthoritativeTeacherDelivery
              ? responseMetadata.deliveryToken
              : null;
            traceRealtimeAuthority('backend.submit', {
              eventType: deliveryToken ? 'teacher_delivery_completed' : 'assistant_response_completed',
              requestKey,
              phase: completedPhase,
              hasDeliveryToken: Boolean(deliveryToken),
            });
            const data = await postRealtimeEvent({
              event_type: deliveryToken ? 'teacher_delivery_completed' : 'assistant_response_completed',
              delivery_token: deliveryToken,
              assistant_response: transcript || null,
              student_response: deliveryToken ? null : (lastRealtimeStudentTranscriptRef.current || null),
            });
            applyRealtimeAuthority(data, realtime);
            realtimeRequestedTurnRef.current.release(requestKey);
            traceRealtimeAuthority('request_key.released', { requestKey, reason: 'backend_acknowledged' });
            lastRealtimeStudentTranscriptRef.current = '';
            if (data.practice_ready === true && data.pedagogical_state?.current_phase === 'PRACTICE_READY') {
              realtime.createResponse(data.phase_instruction, 'lesson_complete');
              return;
            }
            const continued = continueFromAuthority(completedPhase, data, realtime);
            traceRealtimeAuthority('continuation.decision', {
              previousPhase: completedPhase,
              nextPhase: data.pedagogical_state?.current_phase || null,
              responseCreateIssued: continued,
            });
          } catch (error) {
            realtimeRequestedTurnRef.current.release(requestKey);
            console.warn('Realtime state persistence failed safely:', error);
            try {
              const recovered = await postRealtimeEvent({ event_type: 'start_class' });
              applyRealtimeAuthority(recovered, realtime);
              continueFromAuthority(null, recovered, realtime);
            } catch (recoveryError) {
              console.warn('Realtime authoritative reconciliation failed safely:', recoveryError);
            }
          } finally {
            realtimeEventInFlightRef.current = false;
            drainRealtimeCompletion(
              pendingRealtimeTutorDoneRef,
              isMountedRef.current && realtime.connected,
              (pendingCompletion) => realtime.handlers.onTutorDone?.(pendingCompletion),
            );
          }
        },
        onConnectionState: (health) => {
          if (health.connectionState === 'failed' || health.connectionState === 'disconnected') updateVoiceStatus('reconnecting');
        },
        onError: (message) => console.warn('Realtime classroom:', message),
      });
      await realtime.connect(tokenResponse.data.client_secret);
      if (!isMountedRef.current) {
        realtime.close();
        return;
      }
      realtimeRef.current = realtime;
      const startData = await postRealtimeEvent({ event_type: 'start_class' });
      applyRealtimeAuthority(startData, realtime);
      requestCurrentTeacherTurn(startData.phase_instruction, 'START', realtime);
      realtimeStarted = true;
      updateVoiceStatus('speaking');
      setMicActive(true);
    } catch (error) {
      console.warn('Realtime unavailable; using classroom voice fallback.', error);
      realtimeRef.current?.close();
      realtimeRef.current = null;
    }

    if (realtimeStarted) return;

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

  const handleEndClass = () => {
    guidanceRequestRef.current += 1;
    isVoicePausedRef.current = true;
    setIsVoicePaused(true);
    realtimeRef.current?.close();
    realtimeRef.current = null;
    stopAllAudioAndMic();
    updateVoiceStatus('paused');
    setHasStartedVoice(false);
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
        <div className="lesson-brand"><BrandLogo variant="crest" onClick={onExit} /></div>
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
            onClick={hasStartedVoice ? handleEndClass : handleStartClass}
            className={`voice-toggle-pill ${isVoicePaused ? 'paused' : 'active'}`}
            title={!hasStartedVoice ? 'Start the live class' : 'End the live class'}
          >
            {!hasStartedVoice ? '🎙️ Start Class' : '⏹ End Class'}
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
      <div className={`floating-voice-bar ${voiceStatus} ${hasStartedVoice ? 'live-active' : ''}`}>
        <div className="voice-bar-left" onClick={!hasStartedVoice ? handleStartClass : undefined} title={!hasStartedVoice ? 'Start the live class' : undefined}>
          <div className={`voice-avatar-orb ${voiceStatus}`}>
            👩🏾‍🏫
            {voiceStatus === 'speaking' && <span className="ring-pulse green" />}
            {voiceStatus === 'listening' && <span className="ring-pulse blue" />}
            {voiceStatus === 'thinking' && <span className="ring-pulse amber" />}
            {(voiceStatus === 'connecting' || voiceStatus === 'reconnecting') && <span className="ring-pulse amber" />}
          </div>

        </div>

        {!hasStartedVoice && <div className="voice-bar-actions">
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
              title="Replay what Ms Ade just said"
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
        </div>}
      </div>
    </div>
  );
}
