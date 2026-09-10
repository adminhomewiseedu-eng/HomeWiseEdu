import test from 'node:test';
import assert from 'node:assert/strict';
import { teacherDeliveryLooksComplete } from './teacherDelivery.js';

test('rejects praise-only speech as completion of a worked example', () => {
  assert.equal(
    teacherDeliveryLooksComplete('WORKED_EXAMPLE_3', "Brilliant counting, Juliet. You're doing so well."),
    false,
  );
});

test('rejects a vague readiness loop as completion of teaching', () => {
  assert.equal(
    teacherDeliveryLooksComplete('TEACHING', "It's all right, Juliet. Let's get started. Are you ready to jump in?"),
    false,
  );
});

test('rejects a long teaching turn that ends with only a vague invitation', () => {
  assert.equal(teacherDeliveryLooksComplete(
    'TEACHING',
    "We counted the five cubes slowly and carefully. We touched each imagined cube once, saying one, two, three, four, and five in the correct order. Now let's practise a few more times together?",
  ), false);
});

test('accepts a complete teaching turn ending in a concrete counting task', () => {
  assert.equal(teacherDeliveryLooksComplete(
    'TEACHING',
    'We count each object once and keep the numbers in order. I counted one, two, three, four, five. That tells us there are five objects altogether. Juliet, can you count from one to five for me?',
  ), true);
});

test('rejects teaching that sends the learner to find physical objects', () => {
  assert.equal(teacherDeliveryLooksComplete(
    'WORKED_EXAMPLE_2',
    'We have practised counting carefully from one to five and touched each item only once as we counted. Juliet, can you find five objects around you and count them out loud for me?',
  ), false);
});

test('rejects a transition-only response in an assessed phase', () => {
  assert.equal(
    teacherDeliveryLooksComplete('GUIDED_PRACTICE', "Excellent work, Juliet. Let's move to the next step now."),
    false,
  );
});

test('accepts an assessed phase only when it asks a concrete question', () => {
  assert.equal(teacherDeliveryLooksComplete(
    'GUIDED_PRACTICE',
    'Well done, Juliet. For the next step, imagine four counters and add one more. How many counters are there altogether?',
  ), true);
});

test('accepts a complete worked example with a direct handoff question', () => {
  assert.equal(teacherDeliveryLooksComplete(
    'WORKED_EXAMPLE_1',
    'Juliet, imagine five cubes in a row. I count each cube once: one, two, three, four, five. There are five cubes altogether. Juliet, what answer did I get in that example?',
  ), true);
});

test('accepts a complete teacher-led third example without absorbing the understanding check', () => {
  assert.equal(teacherDeliveryLooksComplete(
    'WORKED_EXAMPLE_3',
    'On the cards we have one, two, three, four, and five. After three comes four because four is the next card. That is the complete answer. Now we move to a separate understanding check.',
  ), true);
});
