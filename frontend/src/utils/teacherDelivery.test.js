import test from 'node:test';
import assert from 'node:assert/strict';
import { teacherDeliveryLooksComplete } from './teacherDelivery.js';

test('accepts non-empty authoritative worked-example output without judging its wording', () => {
  assert.equal(
    teacherDeliveryLooksComplete('WORKED_EXAMPLE_3', "Brilliant counting, Juliet. You're doing so well."),
    true,
  );
});

test('accepts non-empty authoritative teaching output without arbitrary wording heuristics', () => {
  assert.equal(
    teacherDeliveryLooksComplete('TEACHING', "It's all right, Juliet. Let's get started. Are you ready to jump in?"),
    true,
  );
});

test('does not use a teaching transcript ending as phase authority', () => {
  assert.equal(teacherDeliveryLooksComplete(
    'TEACHING',
    "We counted the five cubes slowly and carefully. We touched each imagined cube once, saying one, two, three, four, and five in the correct order. Now let's practise a few more times together?",
  ), true);
});

test('accepts a complete teacher-led Level 0 explanation without an abstract question', () => {
  assert.equal(teacherDeliveryLooksComplete(
    'TEACHING',
    'Counting tells us how many objects there are. We say one, two, three, four, five in order while Ms Ade points to each cube once. Next, I will show you three examples.',
  ), true);
});

test('does not make worked-example progression depend on selected English phrases', () => {
  assert.equal(teacherDeliveryLooksComplete(
    'WORKED_EXAMPLE_2',
    'We have practised counting carefully from one to five and touched each item only once as we counted. Juliet, can you find five objects around you and count them out loud for me?',
  ), true);
});

test('accepts a valid short WE2 response with natural alternative wording', () => {
  assert.equal(
    teacherDeliveryLooksComplete('WORKED_EXAMPLE_2', 'Five fingers, counted carefully from one through five.'),
    true,
  );
});

test('rejects empty or punctuation-only teacher output', () => {
  assert.equal(teacherDeliveryLooksComplete('WORKED_EXAMPLE_2', ''), false);
  assert.equal(teacherDeliveryLooksComplete('WORKED_EXAMPLE_2', '...'), false);
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

test('accepts a fully delivered worked example that closes by moving to the next example', () => {
  assert.equal(teacherDeliveryLooksComplete(
    'WORKED_EXAMPLE_1',
    "I point to each cube once while saying the numbers in order: one, two, three, four, five. Each cube gets one number. Then we'll move on to the next example.",
  ), true);
});
