const asList = (value) => Array.isArray(value) ? value.filter(Boolean) : value ? [value] : [];

const WORKED_EXAMPLE_PHASES = [
  'WORKED_EXAMPLE_1',
  'WORKED_EXAMPLE_2',
  'WORKED_EXAMPLE_3',
];

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

  const curriculumExamples = asList(activeDay?.worked_examples?.length ? activeDay.worked_examples : lesson?.examples);

  return {
    teachingNote: messageForPhase('TEACHING'),
    workedExamples: curriculumExamples.length > 0 ? curriculumExamples : deliveredExamples,
    practiceQuestions: asList(activeDay?.practice_questions),
    lessonSummary: messageForPhase('LESSON_SUMMARY'),
  };
}
