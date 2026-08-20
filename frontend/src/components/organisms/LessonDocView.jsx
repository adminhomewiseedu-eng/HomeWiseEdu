import React from 'react';

export default function LessonDocView({ lesson, levelLabel = 'Reception', onProceedToQuiz, practiceReady = false }) {
  if (!lesson) return null;

  return (
    <div className="doc-page">
      {/* Textbook / Study Guide Top Banner */}
      <div className="doc-page-header">
        <div className="doc-badge-row">
          <span className="doc-badge doc-badge-subject">
            {lesson.unit?.subject?.title || 'Academic Pathway'}
          </span>
          <span className="doc-badge doc-badge-level">
            {levelLabel}
          </span>
          <span className="doc-badge doc-badge-num">
            Lesson {lesson.order_num || 1}
          </span>
        </div>
        <h1 className="doc-page-title">{lesson.title}</h1>
        {lesson.topic && <div className="doc-page-topic">Topic: {lesson.topic}</div>}
      </div>

      {/* Main Document Content Flow (Structured from Top to Bottom) */}
      <div className="doc-page-body">

        {/* 1. Learning Objectives */}
        {lesson.objectives && lesson.objectives.length > 0 && (
          <section className="doc-card doc-card-objectives">
            <div className="doc-card-title">
              <span className="icon">🎯</span>
              <h2>1. What We'll Learn Today</h2>
            </div>
            <div className="doc-obj-list">
              {lesson.objectives.map((obj, i) => (
                <div key={i} className="doc-obj-item">
                  <div className="doc-obj-num">{i + 1}</div>
                  <p>{obj}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 2. Core Learning Content / Key Concept */}
        {lesson.learn_content && (
          <section className="doc-card doc-card-learn">
            <div className="doc-card-title">
              <span className="icon">💡</span>
              <h2>2. Let's Learn the Concept</h2>
            </div>
            <div className="doc-learn-text">
              {lesson.learn_content.split('\n\n').map((paragraph, i) => (
                <p key={i}>{paragraph}</p>
              ))}
            </div>
          </section>
        )}

        {/* 3. Worked Examples in Action */}
        {lesson.examples && lesson.examples.length > 0 && (
          <section className="doc-card doc-card-examples">
            <div className="doc-card-title">
              <span className="icon">🧸</span>
              <h2>3. Let's See It in Action!</h2>
            </div>
            <div className="doc-examples-list">
              {lesson.examples.map((ex, i) => (
                <div key={i} className="doc-example-box">
                  <div className="doc-example-head">
                    <span className="tag">Example {i + 1}</span>
                    <span className="calc">{ex.calc || ex.title}</span>
                  </div>
                  {ex.explanation && (
                    <p className="doc-example-desc">{ex.explanation}</p>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 4. Vocabulary & Key Words */}
        {lesson.vocabulary && lesson.vocabulary.length > 0 && (
          <section className="doc-card doc-card-vocab">
            <div className="doc-card-title">
              <span className="icon">🔑</span>
              <h2>4. Word Power (Key Vocabulary)</h2>
            </div>
            <div className="doc-vocab-grid">
              {lesson.vocabulary.map((v, i) => (
                <div key={i} className="doc-vocab-card">
                  <div className="word">{v.word}</div>
                  <div className="def">{v.definition}</div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 5. Key Points to Remember */}
        {lesson.key_points && lesson.key_points.length > 0 && (
          <section className="doc-card doc-card-remember">
            <div className="doc-card-title">
              <span className="icon">🌟</span>
              <h2>5. Remember These!</h2>
            </div>
            <div className="doc-points-list">
              {lesson.key_points.map((kp, i) => (
                <div key={i} className="doc-point-item">
                  <div className="check">✓</div>
                  <p>{kp}</p>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* 6. Scripture Reflection & Character Habit */}
        {(lesson.bible_reflection || lesson.character_connection) && (
          <section className="doc-card doc-card-growth">
            {lesson.bible_reflection && (
              <div className="doc-growth-box scripture">
                <div className="growth-header">
                  <span>✝️</span>
                  <strong>Scripture Reflection</strong>
                </div>
                <p>{lesson.bible_reflection}</p>
              </div>
            )}

            {lesson.character_connection && (
              <div className="doc-growth-box character">
                <div className="growth-header">
                  <span>🌱</span>
                  <strong>Character Habit</strong>
                </div>
                <p>{lesson.character_connection}</p>
              </div>
            )}
          </section>
        )}

        {/* 7. Lesson Practice Progression Action */}
        {onProceedToQuiz && (
          <div className="doc-quiz-cta-box">
            <button className="doc-quiz-btn" onClick={onProceedToQuiz} disabled={!practiceReady}>
              <span>{practiceReady ? "✓ I've Discussed Today's Lesson — Start Practice Quiz!" : 'Complete the guided lesson to unlock practice'}</span>
              <span className="cta-icon">🏆 ➔</span>
            </button>
          </div>
        )}

      </div>
    </div>
  );
}
