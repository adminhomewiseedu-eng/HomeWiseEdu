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

test('accepts a complete worked example with a direct handoff question', () => {
  assert.equal(teacherDeliveryLooksComplete(
    'WORKED_EXAMPLE_1',
    'Juliet, imagine five cubes in a row. I count each cube once: one, two, three, four, five. There are five cubes altogether. Juliet, what answer did I get in that example?',
  ), true);
});
