import React, { useState, useEffect, useCallback, useRef } from 'react';
import QuizCard from '../organisms/QuizCard';
import { lessonAPI, curriculumAPI } from '../../services/api';
import { speechService } from '../../services/speech';
import { advanceAfterFeedback } from '../../utils/voiceFlow';

export default function QuizScreen({ lesson, lessonId, dayNumber = 1, child, onExit, onQuizComplete }) {
  const [activeLesson, setActiveLesson] = useState(lesson || null);
  const effectiveLessonId = lessonId || lesson?.id || 1;
  const studentName = child?.name || 'Student';

  const [qIdx, setQIdx] = useState(0);
  const [selectedOpt, setSelectedOpt] = useState(null);
  const [isAnswered, setIsAnswered] = useState(false);
  const [answersList, setAnswersList] = useState([]);
  const [score, setScore] = useState(0);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [voiceFeedbackStatus, setVoiceFeedbackStatus] = useState('Cheering you on! 🌟');
  const [quizQuestions, setQuizQuestions] = useState([]);
  const [loadError, setLoadError] = useState('');
  const [isLoadingQuiz, setIsLoadingQuiz] = useState(true);

  const isMountedRef = useRef(true);
  const spokenQuestionIdRef = useRef(null);

  // Play audio safely using authoritative single audio coordinator
  const playTutorVoice = useCallback(async (textToSpeak) => {
    if (!textToSpeak || !isMountedRef.current) return;
    return speechService.playAuthoritativeAudio(
      textToSpeak,
      () => {
        if (isMountedRef.current) setIsSpeaking(true);
      },
      () => {
        if (isMountedRef.current) setIsSpeaking(false);
      }
    );
  }, []);

  // Load lesson details and quiz questions if needed
  useEffect(() => {
    isMountedRef.current = true;

    if (!activeLesson?.title) {
      curriculumAPI.getLessonDetail(effectiveLessonId)
        .then((res) => {
          if (res.data && isMountedRef.current) {
            setActiveLesson(res.data);
          }
        })
        .catch((err) => console.error('Failed to load quiz questions:', err));
    }
    lessonAPI.getQuiz(child?.id || 1, effectiveLessonId, dayNumber)
      .then((res) => {
        if (!isMountedRef.current) return;
        const loadedQuestions = Array.isArray(res.data) ? res.data : [];
        setQuizQuestions(loadedQuestions);
        if (!loadedQuestions.length) setLoadError('No reviewed quiz is configured for this lesson.');
      })
      .catch((err) => {
        if (isMountedRef.current) setLoadError(err.response?.data?.detail || 'Practice quiz is not ready yet.');
      })
      .finally(() => {
        if (isMountedRef.current) setIsLoadingQuiz(false);
      });

    return () => {
      isMountedRef.current = false;
      speechService.cancelAllSpeech();
    };
  }, [effectiveLessonId, dayNumber, child?.id]);

  const questions = quizQuestions;
  const currentQ = questions[qIdx] || questions[0];

  // Speak opening question prompt aloud once per unique question
  useEffect(() => {
    if (!currentQ || isAnswered) return;

    // Prevent duplicate speech for the same question on rerenders/StrictMode
    const questionKey = `${currentQ.id || qIdx}_${qIdx}`;
    if (spokenQuestionIdRef.current === questionKey) return;

    const questionIntro = qIdx === 0
      ? `Ready ${studentName}? Here is your first question: ${currentQ.question}`
      : `Question ${qIdx + 1}: ${currentQ.question}`;

    setVoiceFeedbackStatus(`Reading Question ${qIdx + 1}…`);
    const timer = setTimeout(() => {
      if (isMountedRef.current && !isAnswered) {
        spokenQuestionIdRef.current = questionKey;
        playTutorVoice(questionIntro);
      }
    }, 250);

    return () => {
      clearTimeout(timer);
      // Strict Mode can clean up the first effect before playback; allow the
      // replacement effect to own the single narration.
      if (spokenQuestionIdRef.current === questionKey) {
        spokenQuestionIdRef.current = null;
      }
    };
  }, [qIdx, currentQ, studentName, isAnswered, playTutorVoice]);

  if (!questions.length) {
    return (
      <div style={{ height: '100vh', background: '#FAF7FD', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--plum)' }}>
        <div style={{ textAlign: 'center' }}>
          <h2>{isLoadingQuiz ? 'Loading quiz assessment...' : (loadError || 'No quiz questions are available.')}</h2>
          {!isLoadingQuiz && <button className="quiz-submit" onClick={onExit}>Back to Dashboard</button>}
        </div>
      </div>
    );
  }

  const handleSubmitAnswer = async () => {
    if (!selectedOpt || isAnswered) return;
    speechService.cancelAllSpeech();
    setIsAnswered(true);

    const isCorrect = String(selectedOpt).trim().toLowerCase() === String(currentQ.correct_answer).trim().toLowerCase();
    const finalScore = isCorrect ? score + 1 : score;
    if (isCorrect) setScore(finalScore);

    const updatedAnswers = [...answersList, { question_id: currentQ.id, selected_answer: selectedOpt }];
    setAnswersList(updatedAnswers);

    // Dynamic, interactive spoken feedback from Ms. Ade
    let spokenReaction = '';
    if (isCorrect) {
      const compliments = [
        `Great job, ${studentName}! That's exactly right.`,
        `Spot on, ${studentName}! Wonderful work!`,
        `Brilliant answer, ${studentName}! You nailed it.`,
        `Excellent thinking, ${studentName}! That is correct.`
      ];
      spokenReaction = compliments[qIdx % compliments.length];
      if (currentQ.explanation_correct) {
        spokenReaction += ` ${currentQ.explanation_correct}`;
      }
      setVoiceFeedbackStatus('🎉 Correct! Great job!');
    } else {
      const guidance = [
        `Good try, ${studentName}!`,
        `Nice effort, ${studentName}!`,
        `Good thinking, ${studentName}!`
      ];
      spokenReaction = guidance[qIdx % guidance.length];
      if (currentQ.explanation_incorrect) {
        spokenReaction += ` Remember: ${currentQ.explanation_incorrect}. Let's try the next one!`;
      } else {
        spokenReaction += ` The correct answer was ${currentQ.correct_answer}. Let's keep learning together!`;
      }
      setVoiceFeedbackStatus('💡 Good effort! Keep going!');
    }

    // The next question is owned by actual feedback playback completion.
    await advanceAfterFeedback(playTutorVoice, spokenReaction, async () => {
      if (!isMountedRef.current) return;
      if (qIdx < questions.length - 1) {
        setQIdx(qIdx + 1);
        setSelectedOpt(null);
        setIsAnswered(false);
      } else {
        const effectiveChildId = child?.id || 1;
        try {
          const res = await lessonAPI.submitQuiz(effectiveChildId, effectiveLessonId, dayNumber, updatedAnswers);
          onQuizComplete(res.data);
        } catch (e) {
          const pct = Math.round((finalScore / questions.length) * 100);
          onQuizComplete({
            score: finalScore,
            total_questions: questions.length,
            percentage: pct,
            xp_earned: 20 + (finalScore * 5),
            passed: pct >= 60,
            feedback: pct === 100 ? "Perfect score! 🏆" : `You scored ${pct}%!`
          });
        }
      }
    });
  };

  return (
    <div className="lesson-screen voice-first-mode quiz-screen">
      {/* Top Bar Navigation */}
      <div className="lesson-bar">
        <div className="exit" onClick={onExit} style={{ cursor: 'pointer' }} title="Back to Dashboard">
          ←
        </div>
        <div className="meta">
          <span className="crumb">Practice Quiz</span>
          <h2>{activeLesson?.title || 'Lesson Assessment'}</h2>
        </div>
      </div>

      {/* Floating Voice Status Orb */}
      <main className="quiz-main">
        <div className="quiz-shell">
          <QuizCard
            questionNumber={qIdx + 1}
            totalQuestions={questions.length}
            questionData={currentQ}
            selectedOption={selectedOpt}
            isAnswered={isAnswered}
            onSelectOption={(opt) => !isAnswered && setSelectedOpt(opt)}
            onSubmitAnswer={handleSubmitAnswer}
          />
        </div>
      </main>

      <div className={`quiz-voice-bar ${isSpeaking ? 'speaking' : ''}`}>
        <span className="quiz-voice-avatar">{isSpeaking ? '🗣️' : '👩🏾‍🏫'}</span>
        <div>
          <strong>Ms. Ade</strong>
          <span>{isSpeaking ? 'Speaking to you…' : voiceFeedbackStatus}</span>
        </div>
      </div>
    </div>
  );
}
