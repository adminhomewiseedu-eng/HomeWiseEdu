import React from 'react';
import { buildLessonNotes } from '../../utils/lessonNotes';

const asList = (value) => Array.isArray(value) ? value.filter(Boolean) : value ? [value] : [];
const paragraphs = (value) => String(value || '').split(/\n\s*\n/).map((part) => part.trim()).filter(Boolean);

function Section({ label, icon, tone = '', children }) {
  return <section className={`doc-chapter ${tone}`}>
    <div className="doc-chapter-heading"><span>{icon}</span><h2>{label}</h2><i /></div>
    <div className="doc-chapter-content">{children}</div>
  </section>;
}

export default function LessonDocView({ lesson, levelLabel = 'Reception', dayNumber = 1, activityType = 'Explore', onProceedToQuiz, practiceReady = false, conversationMessages = [] }) {
  if (!lesson) return null;

  const activeDay = lesson.days?.find((day) => Number(day.day_number) === Number(dayNumber)) || lesson.days?.[0] || {};
  const objectives = asList(activeDay.learning_objectives?.length ? activeDay.learning_objectives : lesson.objectives);
  const concept = activeDay.key_concept || lesson.learn_content;
  const introduction = activeDay.ai_script;
  const notes = buildLessonNotes(lesson, activeDay, conversationMessages);
  const examples = notes.workedExamples;
  const practiceQuestions = notes.practiceQuestions;
  const vocabulary = asList(activeDay.vocabulary?.length ? activeDay.vocabulary : lesson.vocabulary);
  const remember = asList(lesson.key_points);
  const realWorld = activeDay.real_world_context;
  const origin = activeDay.origin_of_knowledge;
  const visualSupport = activeDay.visual_support;
  const character = activeDay.character_reference || lesson.character_connection;
  const scripture = [activeDay.bible_reference, activeDay.biblical_theme, activeDay.biblical_application || lesson.bible_reflection].filter(Boolean);
  const recommendations = asList(activeDay.reading_recommendations);

  return <article className="doc-page">
    <header className="doc-page-header">
      <div className="doc-badge-row">
        <span className="doc-badge doc-badge-subject">{lesson.unit?.subject?.title || 'Academic Pathway'}</span>
        <span className="doc-badge doc-badge-level">{levelLabel}</span>
        <span className="doc-badge doc-badge-num">Lesson {lesson.order_num || 1}</span>
      </div>
      <h1 className="doc-page-title">{lesson.title}</h1>
      <div className="doc-page-topic">{lesson.topic || activeDay.title || lesson.title}</div>
      <div className="doc-day-strip"><span>Day {dayNumber}</span><span>{activityType}</span><span>{activeDay.estimated_duration || 'Guided lesson'}</span></div>
    </header>

    <div className="doc-page-body">
      {origin && <Section label="Origin of Knowledge" icon="🕰️" tone="origin"><div className="doc-reading-copy">{paragraphs(origin).map((text, i) => <p key={i}>{text}</p>)}</div></Section>}

      {objectives.length > 0 && <Section label="Learning Objectives" icon="🎯" tone="objectives">
        <div className="doc-obj-grid">{objectives.map((objective, i) => <div className="doc-obj-item" key={i}><div className="doc-obj-num">{i + 1}</div><p>{objective}</p></div>)}</div>
      </Section>}

      {introduction && <Section label="Introduction" icon="👋" tone="introduction"><div className="doc-intro-callout">{paragraphs(introduction).map((text, i) => <p key={i}>{text}</p>)}</div></Section>}

      {concept && <Section label="The Lesson" icon="📖" tone="lesson">
        <div className="doc-reading-copy">{paragraphs(concept).map((text, i) => <p key={i}>{text}</p>)}</div>
        {notes.teachingNote && <div className="doc-live-note"><strong>Ms. Ade's teaching note</strong><p>{notes.teachingNote}</p></div>}
        {visualSupport && <aside className="doc-visual-note"><strong>Look and notice</strong><span>{visualSupport}</span></aside>}
      </Section>}

      {examples.length > 0 && <Section label="Worked Examples" icon="🧩" tone="examples">
        <div className="doc-examples-list">{examples.map((example, i) => {
          const item = typeof example === 'string' ? { question: example } : example || {};
          const question = item.question || item.title || item.calc || `Example ${i + 1}`;
          const steps = asList(item.steps || item.hints || item.explanation);
          const answer = item.answer || item.solution;
          return <div className="doc-example-box" key={i}>
            <div className="doc-example-head"><span className="tag">Example {i + 1}</span><strong>{question}</strong></div>
            {steps.length > 0 && <ol className="doc-example-steps">{steps.map((step, n) => <li key={n}>{typeof step === 'string' ? step : JSON.stringify(step)}</li>)}</ol>}
            {answer && <div className="doc-example-answer"><span>Answer</span>{String(answer)}</div>}
          </div>;
        })}</div>
      </Section>}

      {practiceQuestions.length > 0 && <Section label="Practice Prompts" icon="✏️" tone="practice-prompts">
        <div className="doc-prompts-list">{practiceQuestions.map((prompt, i) => {
          const item = typeof prompt === 'string' ? { question: prompt } : prompt || {};
          return <div className="doc-prompt-item" key={i}><span>{i + 1}</span><p>{item.question || item.q || item.title || String(prompt)}</p></div>;
        })}</div>
      </Section>}

      {(realWorld || vocabulary.length > 0) && <div className="doc-two-column">
        {realWorld && <Section label="Real-Life Connection" icon="🏡" tone="real-world"><p className="doc-compact-copy">{realWorld}</p></Section>}
        {vocabulary.length > 0 && <Section label="Keywords" icon="🔑" tone="vocabulary"><div className="doc-vocab-list">{vocabulary.map((entry, i) => {
          const word = typeof entry === 'string' ? entry : entry.word || entry.term;
          const definition = typeof entry === 'string' ? '' : entry.definition || entry.meaning;
          return <div className="doc-vocab-card" key={i}><strong>{word}</strong>{definition && <span>{definition}</span>}</div>;
        })}</div></Section>}
      </div>}

      {remember.length > 0 && <Section label="Things to Remember" icon="🌟" tone="remember"><div className="doc-points-list">{remember.map((point, i) => <div className="doc-point-item" key={i}><div className="check">✓</div><p>{point}</p></div>)}</div></Section>}

      {(character || scripture.length > 0) && <div className="doc-two-column growth">
        {character && <Section label="Character Connection" icon="🌱" tone="character"><p className="doc-compact-copy">{character}</p></Section>}
        {scripture.length > 0 && <Section label="Bible Connection" icon="✝️" tone="scripture"><div className="doc-reading-copy compact">{scripture.map((text, i) => <p key={i}>{text}</p>)}</div></Section>}
      </div>}

      {recommendations.length > 0 && <Section label="Reading Recommendation" icon="📚" tone="reading"><p className="doc-compact-copy">{recommendations.join(' · ')}</p></Section>}

      <Section label="Lesson Summary" icon="📝" tone="summary"><p className="doc-compact-copy">{notes.lessonSummary || `Today we are learning ${lesson.topic || lesson.title}. Keep the key idea in mind as you explain your thinking, practise with Ms. Ade, and apply it independently.`}</p></Section>

      {onProceedToQuiz && <div className="doc-quiz-cta-box">
        <div><strong>{practiceReady ? 'Lesson discussion complete' : 'Keep learning with Ms. Ade'}</strong><p>{practiceReady ? 'Your practice quiz is ready.' : 'The quiz unlocks after the guided lesson and mastery check.'}</p></div>
        <button className="doc-quiz-btn" onClick={onProceedToQuiz} disabled={!practiceReady}>{practiceReady ? 'Start Practice Quiz 🏆' : 'Practice Quiz Locked'}</button>
      </div>}
    </div>
  </article>;
}
