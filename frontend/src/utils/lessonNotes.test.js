import test from 'node:test';
import assert from 'node:assert/strict';
import { buildLessonNotes } from './lessonNotes.js';

test('keeps curriculum practice prompts separate from worked examples', () => {
  const notes = buildLessonNotes(
    { examples: [] },
    { practice_questions: ['Explain counting to five.'] },
    []
  );

  assert.deepEqual(notes.workedExamples, []);
  assert.deepEqual(notes.practiceQuestions, ['Explain counting to five.']);
});

test('collects one persisted tutor response for each worked-example phase', () => {
  const notes = buildLessonNotes(
    { examples: [{ title: 'Blueprint example' }] },
    { practice_questions: [] },
    [
      { sender: 'tutor', phase: 'WORKED_EXAMPLE_1', text: 'First example' },
      { sender: 'tutor', phase: 'WORKED_EXAMPLE_2', text: 'Second example' },
      { sender: 'tutor', phase: 'WORKED_EXAMPLE_3', text: 'Third example' },
    ]
  );

  assert.deepEqual(notes.workedExamples.map((example) => example.question), [
    'First example',
    'Second example',
    'Third example',
  ]);
});

test('uses the newest response when a pedagogical phase is repeated', () => {
  const notes = buildLessonNotes(
    { examples: [] },
    {},
    [
      { sender: 'tutor', phase: 'TEACHING', text: 'Initial teaching' },
      { sender: 'tutor', phase: 'TEACHING', text: 'Clarified teaching' },
      { sender: 'tutor', phase: 'LESSON_SUMMARY', text: 'Final summary' },
    ]
  );

  assert.equal(notes.teachingNote, 'Clarified teaching');
  assert.equal(notes.lessonSummary, 'Final summary');
});

