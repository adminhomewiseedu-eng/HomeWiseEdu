import React, { useState, useEffect } from 'react';
import EvidenceForm from '../organisms/EvidenceForm';
import { evidenceAPI, curriculumAPI } from '../../services/api';
import { speechService } from '../../services/speech';

export default function EvidenceSubmitScreen({ lesson, lessonId, dayNumber = 1, child, quizResult, onExit, onSubmitSuccess }) {
  const [activeLesson, setActiveLesson] = useState(lesson || null);
  const effectiveLessonId = lessonId || lesson?.id || 1;

  useEffect(() => {
    if (!activeLesson?.title) {
      curriculumAPI.getLessonDetail(effectiveLessonId)
        .then((res) => {
          if (res.data) setActiveLesson(res.data);
        })
        .catch((err) => console.error('Failed to load lesson for evidence submit:', err));
    }
  }, [effectiveLessonId, activeLesson]);

  const studentName = child?.name || 'Student';
  const subjectName = activeLesson?.unit?.subject?.title || 'Mathematics';
  const lessonTitle = activeLesson?.title || 'Lesson Practice';
  const taskDesc = activeLesson?.default_evidence_task || 'Draw, explain, or upload your solution to demonstrate your understanding.';

  const [text, setText] = useState('Here is my working and explanation for today\'s lesson.');
  const [file, setFile] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [tutorStatus, setTutorStatus] = useState('Ready to check your work');
  const [submitError, setSubmitError] = useState('');

  const quizScore = quizResult?.score ?? 0;
  const quizTotal = quizResult?.total_questions ?? 3;
  const quizPercentage = quizResult?.percentage ?? Math.round((quizScore / quizTotal) * 100);

  const handleSubmit = async () => {
    setSubmitting(true);
    setSubmitError('');
    setTutorStatus('Checking your work…');
    speechService.playAuthoritativeAudio('Let me take a look at your work...').catch(() => {});

    const formData = new FormData();
    formData.append('child_id', child?.id || 1);
    formData.append('lesson_id', effectiveLessonId);
    formData.append('day_number', dayNumber);
    formData.append('subject', subjectName);
    formData.append('lesson_title', lessonTitle);
    formData.append('skill', activeLesson?.objectives?.[0] || 'Core Skill Mastery');
    formData.append('content', text);
    if (file) formData.append('file', file);

    try {
      const res = await evidenceAPI.submitEvidence(formData);
      const evalData = res.data;
      setTimeout(() => {
        setTutorStatus('Verified ✅');
        setTimeout(() => onSubmitSuccess(evalData, quizResult), 1800);
      }, 1500);
    } catch (e) {
      setTutorStatus('Submission needs attention');
      setSubmitError(e.response?.data?.detail || 'We could not submit your evidence. Please check your connection and try again.');
      setSubmitting(false);
    }
  };

  return (
    <div className="lesson-screen evidence-screen">
      <div className="lesson-bar">
        <div className="exit" onClick={onExit} style={{ cursor: 'pointer' }}>←</div>
        <div>
          <div className="lb-title">{lessonTitle}</div>
          <div className="lb-sub">{subjectName} · Submit your evidence</div>
        </div>
        <div className="lb-progress">
          <div className="track"><span style={{ width: '90%' }} /></div>
        </div>
        <div className="pill" style={{ background: '#DCFCE7', color: '#166534' }}>📤 Evidence</div>
      </div>

      <main className="evidence-main">
        <section className="quiz-complete-banner">
          <div className="quiz-complete-icon">🏆</div>
          <div className="quiz-complete-copy">
            <span>Quiz complete</span>
            <h1>Wonderful effort, {studentName}!</h1>
            <p>Ms. Ade is proud of your work. Add one piece of learning evidence to complete today’s lesson.</p>
          </div>
          <div className="quiz-result-score">
            <strong>{quizScore}/{quizTotal}</strong>
            <span>{quizPercentage}% score</span>
          </div>
        </section>

        <div className="evidence-grid">
          <div>
            {submitError && <div className="evidence-error" role="alert">{submitError}</div>}
          <EvidenceForm
            taskDescription={taskDesc}
            textContent={text}
            onTextChange={setText}
            fileName={file?.name}
            onFileSelect={(e) => e.target.files && setFile(e.target.files[0])}
            onSubmit={handleSubmit}
            isSubmitting={submitting}
          />
          </div>
          <aside className="evidence-next-card">
            <div className="evidence-tutor-avatar">👩🏾‍🏫</div>
            <span className="evidence-eyebrow">Ms. Ade</span>
            <h2>{tutorStatus}</h2>
            <p>Your explanation or uploaded work helps build a real learning portfolio—not just a quiz score.</p>
            <div className="evidence-next-steps">
              <div><b>1</b><span>Share what you learned</span></div>
              <div><b>2</b><span>Ms. Ade evaluates it</span></div>
              <div><b>3</b><span>Verified work enters your portfolio</span></div>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
