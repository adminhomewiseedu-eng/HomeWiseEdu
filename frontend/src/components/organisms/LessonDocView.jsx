import React from 'react';

const TABS = [
  { id: 0, label: '🎯 Objectives' },
  { id: 1, label: '📖 Learn' },
  { id: 2, label: '📐 Examples' },
  { id: 3, label: '🔑 Words' },
  { id: 4, label: '✅ Remember' },
];

export default function LessonDocView({ lesson, activeTab, onSelectTab, levelLabel = 'Level 4' }) {
  if (!lesson) return null;

  return (
    <div className="doc">
      <div className="doc-header">
        <div className="badge2">
          Lesson {lesson.order_num || 1} · {levelLabel}
        </div>
        <h1>{lesson.title}</h1>
      </div>

      <div className="doc-tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`doc-tab ${activeTab === t.id ? 'active' : ''}`}
            onClick={() => onSelectTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="doc-content">
        {activeTab === 0 && (
          <div className="doc-section">
            <h2>What you'll learn today</h2>
            {lesson.objectives?.map((obj, i) => (
              <div key={i} className="doc-obj">
                <div className="n">{i + 1}</div>
                <p style={{ margin: 0 }}>{obj}</p>
              </div>
            ))}
          </div>
        )}

        {activeTab === 1 && (
          <div className="doc-section">
            <h2>Core Learning Content</h2>
            <div style={{ whiteSpace: 'pre-line', lineHeight: 1.7, fontSize: 16 }}>{lesson.learn_content}</div>
          </div>
        )}

        {activeTab === 2 && (
          <div className="doc-section">
            <h2>Let's see it in action</h2>
            {lesson.examples?.map((ex, i) => (
              <div key={i} className="example" style={{ borderLeftColor: i === 1 ? 'var(--grape)' : undefined }}>
                <div className="calc">{ex.calc || ex.title}</div>
                <p style={{ margin: '8px 0 0', fontSize: 14 }}>{ex.explanation}</p>
              </div>
            ))}
          </div>
        )}

        {activeTab === 3 && (
          <div className="doc-section">
            <h2>Key words</h2>
            <div className="vocab-grid">
              {lesson.vocabulary?.map((v, i) => (
                <div key={i} className="vocab">
                  <div className="w">{v.word}</div>
                  <div className="d">{v.definition}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {activeTab === 4 && (
          <div className="doc-section">
            <h2>Remember these!</h2>
            {lesson.key_points?.map((kp, i) => (
              <div key={i} className="keypoint">
                <div className="c">✓</div>
                <p style={{ margin: 0 }}>{kp}</p>
              </div>
            ))}
            {lesson.bible_reflection && (
              <div style={{ marginTop: 20, padding: 14, background: '#F3E8FF', borderRadius: 12, borderLeft: '4px solid var(--plum)' }}>
                <div style={{ fontWeight: 800, fontSize: 13, color: 'var(--plum)', marginBottom: 4 }}>✝️ Scripture Reflection</div>
                <div style={{ fontSize: 13, color: 'var(--ink)' }}>{lesson.bible_reflection}</div>
              </div>
            )}
            {lesson.character_connection && (
              <div style={{ marginTop: 12, padding: 14, background: '#FEF3C7', borderRadius: 12, borderLeft: '4px solid var(--sun)' }}>
                <div style={{ fontWeight: 800, fontSize: 13, color: '#92400E', marginBottom: 4 }}>🌟 Character Habit</div>
                <div style={{ fontSize: 13, color: 'var(--ink)' }}>{lesson.character_connection}</div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
