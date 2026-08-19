import React, { useState, useEffect } from 'react';
import QuizCard from '../organisms/QuizCard';
import TutorHeader from '../organisms/TutorHeader';
import TutorChatStream from '../organisms/TutorChatStream';
import { lessonAPI, curriculumAPI } from '../../services/api';
import { speechService } from '../../services/speech';

export default function QuizScreen({ lesson, lessonId, child, onExit, onQuizComplete }) {
  const [activeLesson, setActiveLesson] = useState(lesson || null);
  const effectiveLessonId = lessonId || lesson?.id || 1;

  useEffect(() => {
    if (!activeLesson?.quiz_questions?.length) {
      curriculumAPI.getLessonDetail(effectiveLessonId)
        .then((res) => {
          if (res.data) setActiveLesson(res.data);
        })
        .catch((err) => console.error('Failed to load quiz questions:', err));
    }
  }, [effectiveLessonId, activeLesson]);

  const questions = activeLesson?.quiz_questions?.length ? activeLesson.quiz_questions : [];
  const [qIdx, setQIdx] = useState(0);
  const [selectedOpt, setSelectedOpt] = useState(null);
  const [isAnswered, setIsAnswered] = useState(false);
  const [answersList, setAnswersList] = useState([]);
  const [score, setScore] = useState(0);
  const [messages, setMessages] = useState([
    { sender: 'tutor', text: `Ready, ${child?.name || 'Student'}? Here's your first question. Take your time! 🌟` },
  ]);

  if (!questions.length) {
    return (
      <div className="wrap pad" style={{ textAlign: 'center', padding: '100px 0' }}>
        <h2>Loading quiz...</h2>
      </div>
    );
  }

  const currentQ = questions[qIdx] || questions[0];

  const handleSubmitAnswer = async () => {
    if (!selectedOpt || isAnswered) return;
    setIsAnswered(true);

    const isCorrect = String(selectedOpt).trim().toLowerCase() === String(currentQ.correct_answer).trim().toLowerCase();
    const finalScore = isCorrect ? score + 1 : score;
    if (isCorrect) setScore(finalScore);

    const updatedAnswers = [...answersList, { question_id: currentQ.id, selected_answer: selectedOpt }];
    setAnswersList(updatedAnswers);

    const feedback = isCorrect ? currentQ.explanation_correct : currentQ.explanation_incorrect;
    setMessages((prev) => [
      ...prev,
      { sender: 'me', text: String(selectedOpt) },
      { sender: 'tutor', text: feedback || (isCorrect ? 'Correct! 🌟' : 'Good try!') }
    ]);
    speechService.speak(feedback || (isCorrect ? 'Great job!' : 'Good try!'));

    setTimeout(async () => {
      if (qIdx < questions.length - 1) {
        setQIdx(qIdx + 1);
        setSelectedOpt(null);
        setIsAnswered(false);
      } else {
        const effectiveChildId = child?.id || 1;
        try {
          const res = await lessonAPI.submitQuiz(effectiveChildId, effectiveLessonId, updatedAnswers);
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
    }, 2000);
  };

  return (
    <div className="lesson-screen">
      <div className="lesson-bar">
        <div className="exit" onClick={onExit} style={{ cursor: 'pointer' }}>←</div>
        <div>
          <div className="lb-title">{activeLesson?.title || 'Lesson Quiz'}</div>
          <div className="lb-sub">Question {qIdx + 1} of {questions.length}</div>
        </div>
        <div className="lb-progress">
          <div className="track">
            <span style={{ width: `${Math.round(((qIdx + 1) / questions.length) * 100)}%` }} />
          </div>
        </div>
        <div className="pill" style={{ background: '#FEF3C7', color: '#92400E' }}>❓ Quiz</div>
      </div>

      <div className="lesson-body">
        <div className="doc-side" style={{ display: 'flex', alignItems: 'center' }}>
          <QuizCard
            questionNumber={qIdx + 1}
            totalQuestions={questions.length}
            questionData={currentQ}
            selectedOption={selectedOpt}
            isAnswered={isAnswered}
            onSelectOption={setSelectedOpt}
            onSubmitAnswer={handleSubmitAnswer}
          />
        </div>
        <div className="tutor-side">
          <TutorHeader studentName={child?.name || 'Student'} status="Cheering you on!" />
          <TutorChatStream messages={messages} />
        </div>
      </div>
    </div>
  );
}
