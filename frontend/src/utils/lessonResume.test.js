import assert from 'node:assert/strict';
import { it } from 'node:test';
import { resolveLessonResume } from './lessonResume.js';

it('resumes an in-progress active question instead of starting a greeting', () => {
  const result = resolveLessonResume({
    practice_ready: false,
    pedagogical_state: {
      current_phase: 'APPLICATION',
      active_phase: 'APPLICATION',
      active_question: 'What fraction of the six slices remains?',
      worked_examples_completed: 3,
    },
  });
  assert.equal(result.mode, 'active_question');
  assert.equal(result.question, 'What fraction of the six slices remains?');
});

it('identifies a genuinely empty session as new', () => {
  assert.equal(resolveLessonResume({ pedagogical_state: {} }).mode, 'new');
});
