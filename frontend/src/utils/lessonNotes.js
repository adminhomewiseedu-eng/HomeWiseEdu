const asList = (value) => Array.isArray(value) ? value.filter(Boolean) : value ? [value] : [];

const WORKED_EXAMPLE_PHASES = [
  'WORKED_EXAMPLE_1',
  'WORKED_EXAMPLE_2',
  'WORKED_EXAMPLE_3',
];

const visualExamples = (value) => String(value || '')
  .split(/(?<=[.!?])\s+/)
  .map((part) => part.trim())
  .filter(Boolean);

const uniqueItems = (items) => {
  const seen = new Set();
  return items.filter((item) => {
    const marker = typeof item === 'string' ? item.trim().toLowerCase() : JSON.stringify(item);
    if (!marker || seen.has(marker)) return false;
    seen.add(marker);
    return true;
  });
};

export function buildLessonNotes(lesson, activeDay, conversationMessages = []) {
  const tutorMessages = conversationMessages.filter(
    (message) => message?.sender === 'tutor' && message.text
  );

  const messageForPhase = (phase) => {
    const matches = tutorMessages.filter((message) => message.phase === phase);
    return matches.at(-1)?.text || '';
  };

  const deliveredExamples = WORKED_EXAMPLE_PHASES
    .map((phase) => messageForPhase(phase))
    .filter(Boolean)
    .map((text) => ({ question: text, deliveredByTutor: true }));

  // Keep the written note complete even when an older API response does not yet
  // expose the server-composed worked_examples property.
  const curriculumExamples = uniqueItems([
    ...asList(activeDay?.worked_examples),
    ...asList(lesson?.examples),
    ...visualExamples(activeDay?.visual_support),
  ]);

  return {
    teachingNote: messageForPhase('TEACHING'),
    workedExamples: curriculumExamples.length > 0 ? curriculumExamples : deliveredExamples,
    practiceQuestions: asList(activeDay?.practice_questions),
    lessonSummary: messageForPhase('LESSON_SUMMARY'),
  };
}
