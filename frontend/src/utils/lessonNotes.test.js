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

test('uses the API-authored day example plan as the written note source', () => {
  const notes = buildLessonNotes(
    { examples: [] },
    {
      worked_examples: ['Count five cubes.', 'Count five fingers.', 'Match five cards to five objects.'],
      practice_questions: ['How many objects are there?'],
    },
    [{ sender: 'tutor', phase: 'WORKED_EXAMPLE_1', text: 'An improvised transcript.' }]
  );

  assert.deepEqual(notes.workedExamples, [
    'Count five cubes.',
    'Count five fingers.',
    'Match five cards to five objects.',
  ]);
  assert.deepEqual(notes.practiceQuestions, ['How many objects are there?']);
});

test('shows every authored lesson and visual example in the written note', () => {
  const notes = buildLessonNotes(
    { examples: ['Count five cubes.'] },
    { visual_support: 'Count five fingers. Match five cards to five objects.' },
    []
  );

  assert.deepEqual(notes.workedExamples, [
    'Count five cubes.',
    'Count five fingers.',
    'Match five cards to five objects.',
  ]);
});

test('keeps authored examples authoritative over spoken transcript wording', () => {
  const notes = buildLessonNotes(
    { examples: [{ title: 'Blueprint example' }] },
    { practice_questions: [] },
    [
      { sender: 'tutor', phase: 'WORKED_EXAMPLE_1', text: 'First example' },
      { sender: 'tutor', phase: 'WORKED_EXAMPLE_2', text: 'Second example' },
      { sender: 'tutor', phase: 'WORKED_EXAMPLE_3', text: 'Third example' },
    ]
  );

  assert.deepEqual(notes.workedExamples, [{ title: 'Blueprint example' }]);
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
