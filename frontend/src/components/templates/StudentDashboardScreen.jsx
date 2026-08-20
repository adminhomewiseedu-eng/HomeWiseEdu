import React, { useEffect } from 'react';
import SubjectProgressRow from '../molecules/SubjectProgressRow';
import { useStudentDashboard } from '../../hooks/useStudentDashboard';

export default function StudentDashboardScreen({ child, onStartLesson, onStartQuiz, onViewPortfolio, onBackToParent }) {
  const getStoredChildId = () => {
    if (child?.id) return Number(child.id);
    try {
      const saved = JSON.parse(localStorage.getItem('activeChild') || '{}');
      if (saved?.id) return Number(saved.id);
    } catch (e) {}
    return null;
  };

  const effectiveChildId = getStoredChildId() || (child?.id ? Number(child.id) : 1);
  const { data, loading, refetch } = useStudentDashboard(effectiveChildId);

  useEffect(() => {
    refetch();
  }, [effectiveChildId, refetch]);

  if (loading || !data) {
    return <div className="wrap pad" style={{ textAlign: 'center', padding: '100px 0' }}><h2>Loading student dashboard...</h2></div>;
  }

  const {
    name = child?.name || 'Student',
    xp = 0,
    streak_days = 1,
    badges_count = 0,
    completed_lessons_count = 0,
    curriculum_state = 'ready',
    today_lesson,
    progress_by_subject = [],
    recent_projects = [],
    learning_evidence = [],
    ai_feedback_snippet
  } = data;

  return (
    <div className="wrap" style={{ paddingBottom: '50px' }}>
      {onBackToParent && (
        <div style={{ display: 'flex', justifyContent: 'flex-start', alignItems: 'center', marginTop: '16px' }}>
          <button 
            onClick={onBackToParent}
            className="btn btn-ghost btn-sm"
            style={{ 
              display: 'inline-flex', 
              alignItems: 'center', 
              gap: '8px', 
              background: 'var(--cream)', 
              border: '1px solid var(--border)',
              fontWeight: 700,
              color: 'var(--plum)',
              padding: '8px 16px',
              borderRadius: '12px',
              cursor: 'pointer'
            }}
          >
            ← Back to Parent Dashboard
          </button>
        </div>
      )}
      <div style={{ background: 'linear-gradient(135deg,var(--teal),var(--sky))', borderRadius: 26, padding: 30, color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'space-between', margin: '16px 0 22px 0', position: 'relative', overflow: 'hidden' }}>
        <div className="hero-blob" style={{ width: 180, height: 180, background: '#fff', opacity: 0.15, top: -50, right: 40 }} />
        <div style={{ position: 'relative', zIndex: 2 }}>
          <h2 style={{ fontSize: 30 }}>Welcome, {name}! 🌟</h2>
          <p style={{ fontWeight: 600, opacity: 0.9, fontSize: 16 }}>
            {completed_lessons_count > 0 ? `${completed_lessons_count} lesson${completed_lessons_count > 1 ? 's' : ''} completed so far!` : "Today's learning path is ready."}
          </p>
        </div>
        <div style={{ position: 'relative', zIndex: 2, background: 'rgba(255,255,255,.2)', borderRadius: 18, padding: '14px 22px', textAlign: 'center' }}>
          <div style={{ fontFamily: 'Baloo 2', fontWeight: 800, fontSize: 32 }}>{xp}</div>
          <div style={{ fontSize: 12, fontWeight: 800, opacity: 0.9 }}>⭐ XP POINTS</div>
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card pad">
          <div className="card-head"><h3>📅 Today's Lesson</h3></div>
          {today_lesson ? (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, background: 'var(--cream)', borderRadius: 16, padding: 18 }}>
                <div style={{ width: 56, height: 56, borderRadius: 16, background: '#FEF3C7', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28 }}>
                  {today_lesson.icon || '📐'}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 800, fontSize: 18, color: 'var(--plum)' }}>{today_lesson.title}</div>
                  <div style={{ fontSize: 13, color: 'var(--ink-soft)', fontWeight: 700 }}>
                    {today_lesson.subject} · {today_lesson.unit} (Lesson {today_lesson.order_num})
                  </div>
                </div>
              </div>
              <button className="btn btn-primary" style={{ width: '100%', marginTop: 16 }} onClick={() => onStartLesson(today_lesson)}>
                ▶ Start Lesson
              </button>
            </>
          ) : curriculum_state === 'no_subjects' ? (
            <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--ink-soft)' }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>📚</div>
              <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--plum)' }}>No subjects assigned yet</div>
              <p style={{ fontSize: 13, marginTop: 4 }}>Ask your parent or administrator to configure your academic pathway.</p>
            </div>
          ) : curriculum_state === 'no_published_lessons' ? (
            <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--ink-soft)' }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>🗓️</div>
              <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--plum)' }}>No published lessons available</div>
              <p style={{ fontSize: 13, marginTop: 4 }}>Your curriculum is being prepared. Please check back soon.</p>
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--ink-soft)' }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>🎉</div>
              <div style={{ fontWeight: 700, fontSize: 16, color: 'var(--plum)' }}>All lessons completed!</div>
              <p style={{ fontSize: 13, marginTop: 4 }}>Great job! Check your portfolio to review your work.</p>
            </div>
          )}
        </div>

        <div className="card pad">
          <div className="card-head"><h3>My Progress</h3></div>
          {progress_by_subject.length > 0 ? (
            progress_by_subject.map((p, i) => (
              <SubjectProgressRow
                key={i}
                icon={p.icon}
                name={p.subject}
                percentage={p.percentage}
                fillBackground={p.color}
              />
            ))
          ) : (
            <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--ink-soft)' }}>
              <p>No subjects loaded.</p>
            </div>
          )}
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 20 }}>
        <div className="card pad">
          <div className="card-head">
            <h3>My Projects</h3>
            <a onClick={onViewPortfolio} style={{ cursor: 'pointer' }}>View all →</a>
          </div>
          {recent_projects.length > 0 ? (
            recent_projects.map((proj, i) => (
              <div key={i} className="ev-row" onClick={onViewPortfolio} style={{ cursor: 'pointer' }}>
                <div className="ai" style={{ background: '#DBEAFE' }}>{proj.icon || '📝'}</div>
                <div className="et">{proj.title}</div>
                <span
                  className="status-chip"
                  style={{
                    background: proj.color || '#F0FDF4',
                    color: proj.status === 'Done' ? '#16A34A' : 'var(--amber)'
                  }}
                >
                  {proj.status === 'Done' ? '✅ Done' : '⏳ In Review'}
                </span>
              </div>
            ))
          ) : (
            <div style={{ textAlign: 'center', padding: '24px 10px', color: 'var(--ink-soft)' }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>🎨</div>
              <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--plum)' }}>No projects submitted yet</div>
              <div style={{ fontSize: 13, marginTop: 4 }}>Complete lesson evidence tasks to build your project portfolio!</div>
            </div>
          )}
        </div>

        <div className="card pad">
          <div className="card-head">
            <h3>Learning Evidence</h3>
            <a onClick={onViewPortfolio} style={{ cursor: 'pointer' }}>Portfolio →</a>
          </div>
          {learning_evidence.length > 0 ? (
            learning_evidence.map((ev, i) => (
              <div key={i} className="ev-row" onClick={onViewPortfolio} style={{ cursor: 'pointer' }}>
                <div className="ai" style={{ background: '#DCFCE7' }}>
                  {ev.submission_type === 'image' ? '🖼️' : ev.submission_type === 'video' ? '🎥' : '📄'}
                </div>
                <div className="et">{ev.subject ? `${ev.subject} · ` : ''}{ev.lesson_title}</div>
                <span
                  className="status-chip"
                  style={{
                    background: ev.verified ? '#F0FDF4' : '#FFF7ED',
                    color: ev.verified ? '#16A34A' : 'var(--amber)'
                  }}
                >
                  {ev.verified ? '✅ Verified' : '⏳ In Review'}
                </span>
              </div>
            ))
          ) : (
            <div style={{ textAlign: 'center', padding: '24px 10px', color: 'var(--ink-soft)' }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>📚</div>
              <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--plum)' }}>No evidence submitted yet</div>
              <div style={{ fontSize: 13, marginTop: 4 }}>Submit work samples and quizzes after finishing lessons.</div>
            </div>
          )}
        </div>
      </div>

      <div className="grid-2" style={{ marginBottom: 56 }}>
        <div className="card pad">
          <div className="card-head"><h3>AI Feedback & Daily Quiz</h3></div>
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', background: '#FBF7FF', borderRadius: 14, padding: 14, marginBottom: 14 }}>
            <div style={{ width: 38, height: 38, borderRadius: '50%', background: 'linear-gradient(135deg,var(--sun),var(--coral))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 19, flexShrink: 0 }}>🤖</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: 'var(--ink)', lineHeight: 1.5 }}>"{ai_feedback_snippet}"</div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 800, color: 'var(--plum)' }}>
              📋 Daily Quiz <span className="pill" style={{ background: '#F0FDF4', color: '#16A34A' }}>{today_lesson?.practice_ready ? 'Ready!' : 'Locked'}</span>
            </div>
            <button className="btn btn-grape btn-sm" disabled={!today_lesson?.practice_ready} onClick={() => onStartQuiz(today_lesson)}>
              Take Quiz →
            </button>
          </div>
        </div>

        <div className="card pad">
          <div className="card-head"><h3>🏆 Rewards</h3></div>
          <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
            <div style={{ flex: 1, background: '#FEF3C7', borderRadius: 14, padding: 14, textAlign: 'center' }}>
              <div style={{ fontSize: 26 }}>⭐</div>
              <div style={{ fontFamily: 'Baloo 2', fontWeight: 800, color: 'var(--plum)' }}>{xp} XP</div>
            </div>
            <div style={{ flex: 1, background: '#DBEAFE', borderRadius: 14, padding: 14, textAlign: 'center' }}>
              <div style={{ fontSize: 26 }}>🔥</div>
              <div style={{ fontFamily: 'Baloo 2', fontWeight: 800, color: 'var(--plum)' }}>{streak_days} day streak</div>
            </div>
            <div style={{ flex: 1, background: '#F0FDF4', borderRadius: 14, padding: 14, textAlign: 'center' }}>
              <div style={{ fontSize: 26 }}>🏅</div>
              <div style={{ fontFamily: 'Baloo 2', fontWeight: 800, color: 'var(--plum)' }}>{badges_count} badges</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn btn-teal btn-sm" style={{ flex: 1 }} onClick={onViewPortfolio}>📁 Portfolio</button>
            <button className="btn btn-ghost btn-sm" style={{ flex: 1, border: '2px solid var(--line)' }} onClick={onViewPortfolio}>🎓 Certificates</button>
          </div>
        </div>
      </div>
    </div>
  );
}
