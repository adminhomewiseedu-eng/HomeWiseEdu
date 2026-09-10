import test from 'node:test';
import assert from 'node:assert/strict';
import { nextAuthoritativeRealtimeTurn } from './realtimeProgression.js';

test('waits for the learner after the opening greeting', () => {
  assert.equal(nextAuthoritativeRealtimeTurn('GREETING', { current_phase: 'TEACHING' }), null);
});

test('deterministically chains every worked-example boundary', () => {
  for (let attempt = 0; attempt < 10; attempt += 1) {
    assert.deepEqual(nextAuthoritativeRealtimeTurn('TEACHING', { current_phase: 'WORKED_EXAMPLE_1' }), { tag: 'teacher_delivery', phase: 'WORKED_EXAMPLE_1' });
    assert.deepEqual(nextAuthoritativeRealtimeTurn('WORKED_EXAMPLE_1', { current_phase: 'WORKED_EXAMPLE_2' }), { tag: 'teacher_delivery', phase: 'WORKED_EXAMPLE_2' });
    assert.deepEqual(nextAuthoritativeRealtimeTurn('WORKED_EXAMPLE_2', { current_phase: 'WORKED_EXAMPLE_3' }), { tag: 'teacher_delivery', phase: 'WORKED_EXAMPLE_3' });
  }
});

test('issues the understanding check once after worked example three', () => {
  assert.deepEqual(nextAuthoritativeRealtimeTurn('WORKED_EXAMPLE_3', { current_phase: 'UNDERSTANDING_CHECK', active_question: '' }), { tag: 'academic_prompt', phase: 'UNDERSTANDING_CHECK' });
  assert.equal(nextAuthoritativeRealtimeTurn('UNDERSTANDING_CHECK', { current_phase: 'UNDERSTANDING_CHECK', active_question: 'What comes after four?' }), null);
});

test('does not create a turn after practice becomes ready', () => {
  assert.equal(nextAuthoritativeRealtimeTurn('LESSON_SUMMARY', { current_phase: 'PRACTICE_READY', practice_ready: true }), null);
});
