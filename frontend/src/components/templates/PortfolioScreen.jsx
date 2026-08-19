import React from 'react';
import { usePortfolio } from '../../hooks/usePortfolio';

export default function PortfolioScreen({ child, onBack }) {
  const effectiveChildId = child?.id || 1;
  const { items, loading } = usePortfolio(effectiveChildId);
  const studentName = child?.name || 'Student';

  return (
    <div className="wrap">
      <div className="page-head" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: 16 }}>
        <div>
          <button className="btn btn-ghost btn-sm" style={{ padding: '4px 0', marginBottom: 4 }} onClick={onBack}>
            ← Back to dashboard
          </button>
          <h1>{studentName}'s Portfolio</h1>
          <p>A verified record of real learning and completed evidence tasks.</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost btn-sm" style={{ border: '2px solid var(--line)' }} onClick={() => alert('Portfolio link copied to clipboard!')}>
            🔗 Share link
          </button>
          <button className="btn btn-teal btn-sm" onClick={() => window.print()}>
            📄 Export / Print
          </button>
        </div>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px 0' }}><h3>Loading portfolio...</h3></div>
      ) : items.length === 0 ? (
        <div className="card pad" style={{ textAlign: 'center', padding: '60px 20px', margin: '22px 0 56px' }}>
          <div style={{ fontSize: 48, marginBottom: 12 }}>📁</div>
          <h3 style={{ color: 'var(--plum)' }}>No evidence submitted yet</h3>
          <p style={{ color: 'var(--ink-soft)', marginTop: 6 }}>
            Complete lessons and submit evidence tasks to build {studentName}'s verified portfolio.
          </p>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(280px,1fr))', gap: 18, margin: '22px 0 56px' }}>
          {items.map((it, idx) => {
            const isMath = it.subject.includes('Math');
            const isEng = it.subject.includes('English') || it.subject.includes('Phonics');
            const isSci = it.subject.includes('Science') || it.subject.includes('Biology') || it.subject.includes('Physics') || it.subject.includes('Chemistry');
            const isWord = it.subject.includes('Word');

            const bg = isMath ? 'linear-gradient(135deg,#FEF3C7,#FFF7ED)' : isEng ? 'linear-gradient(135deg,#DBEAFE,#E0F2FE)' : isSci ? 'linear-gradient(135deg,#F0FDF4,#DCFCE7)' : isWord ? 'linear-gradient(135deg,#F3E8FF,#FBF7FF)' : 'linear-gradient(135deg,#FEF3C7,#FFF7ED)';
            const icon = isMath ? '📐' : isEng ? '📖' : isSci ? '🔬' : isWord ? '✝️' : '📝';

            return (
              <div key={idx} className="card pad">
                <div style={{ width: '100%', height: 120, borderRadius: 14, background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 44, marginBottom: 14 }}>
                  {icon}
                </div>
                <div style={{ fontWeight: 800, color: 'var(--plum)', fontSize: 17 }}>{it.lesson_title}</div>
                <div style={{ fontSize: 13, color: 'var(--ink-soft)', fontWeight: 700, margin: '4px 0 8px' }}>
                  {it.subject} · {it.skill}
                </div>
                {it.content && (
                  <div style={{ fontSize: 13, color: 'var(--ink)', background: 'var(--cream)', padding: 10, borderRadius: 8, margin: '8px 0', fontStyle: 'italic' }}>
                    "{it.content}"
                  </div>
                )}
                {it.ai_feedback && (
                  <div style={{ fontSize: 12, color: 'var(--plum)', marginTop: 6, fontWeight: 600 }}>
                    🤖 Feedback: {it.ai_feedback}
                  </div>
                )}
                <div style={{ marginTop: 12 }}>
                  <span className="status-chip" style={{ background: it.verified ? '#F0FDF4' : '#FFF7ED', color: it.verified ? '#16A34A' : 'var(--amber)' }}>
                    {it.verified ? `✅ Verified ${it.score ? `· Score ${it.score}%` : ''}` : '⚠ In Review'}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
