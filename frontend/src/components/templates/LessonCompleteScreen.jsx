import React, { useEffect } from 'react';
import confetti from 'canvas-confetti';

export default function LessonCompleteScreen({ child, quizResult, onViewPortfolio, onNextLesson }) {
  useEffect(() => {
    try {
      confetti({
        particleCount: 80,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#FBBF24', '#FB6F5E', '#14B8A6', '#38BDF8', '#4ADE80', '#7C3AED']
      });
    } catch (e) {}
  }, []);

  const studentName = child?.name || 'Student';
  const scoreText = quizResult ? `${quizResult.score}/${quizResult.total_questions || 3}` : '3/3';
  const xpEarned = quizResult?.xp_earned || 35;

  return (
    <div className="screen active" id="complete">
      <div className="complete">
        <div className="complete-card">
          <div className="big">🎉</div>
          <span className="section-eyebrow">Lesson Complete</span>
          <h2>Amazing work, {studentName}!</h2>
          <div className="sub">Curriculum Progress Updated · XP Awarded</div>

          <div className="cstats">
            <div className="cstat" style={{ background: '#F0FDF4' }}>
              <div className="v" style={{ color: 'var(--leaf)' }}>{scoreText}</div>
              <div className="l" style={{ color: '#14532D' }}>Quiz Score</div>
            </div>
            <div className="cstat" style={{ background: '#DCFCE7' }}>
              <div className="v" style={{ color: 'var(--teal)' }}>✅</div>
              <div className="l" style={{ color: '#166534' }}>Evidence Verified</div>
            </div>
            <div className="cstat" style={{ background: '#FBF7FF' }}>
              <div className="v" style={{ color: 'var(--grape)' }}>+{xpEarned}</div>
              <div className="l" style={{ color: 'var(--grape)' }}>XP Earned</div>
            </div>
          </div>

          <div style={{ background: 'var(--cream)', borderRadius: 16, padding: 16, display: 'flex', gap: 12, alignItems: 'center', textAlign: 'left', marginBottom: 22 }}>
            <div style={{ width: 40, height: 40, borderRadius: '50%', background: 'linear-gradient(135deg,var(--sun),var(--coral))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, flexShrink: 0 }}>
              👩🏾‍🏫
            </div>
            <div style={{ fontSize: 13, color: 'var(--ink)', fontWeight: 600, lineHeight: 1.6 }}>
              Superb work, {studentName}! Your learning evidence has been saved to your portfolio and your curriculum progress has been updated! 🌟
            </div>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button className="btn btn-ghost" style={{ flex: 1, background: 'var(--cream)', color: 'var(--plum)' }} onClick={onViewPortfolio}>
              📁 Portfolio
            </button>
            <button className="btn btn-primary" style={{ flex: 2 }} onClick={onNextLesson}>
              Continue learning →
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
