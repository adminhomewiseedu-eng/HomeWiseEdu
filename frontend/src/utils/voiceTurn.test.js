import assert from 'node:assert/strict';
import { it } from 'node:test';
import { adaptiveSilenceMs, isStableBargeCandidate, looksLikeTeacherEcho } from './voiceTurn.js';

it('allows a longer pause when a learner is visibly hesitating', () => {
  assert.equal(adaptiveSilenceMs('I think maybe'), 3800);
  assert.equal(adaptiveSilenceMs('The answer is five.'), 2200);
  assert.equal(adaptiveSilenceMs('five'), 3200);
});

it('accepts a growing stable interruption transcript', () => {
  assert.equal(isStableBargeCandidate('what is', 'what is the topic'), true);
  assert.equal(isStableBargeCandidate('what is', 'teacher audio echo'), false);
});

it('does not reject short natural learner interruptions as teacher echo', () => {
  assert.equal(looksLikeTeacherEcho('wait', 'Wait until we count all five stars together.'), false);
  assert.equal(looksLikeTeacherEcho('how many?', 'Now let us see how many apples are left.'), false);
  assert.equal(looksLikeTeacherEcho('five', 'There are five counters on the table.'), false);
});

it('still rejects a substantial transcript copied from teacher playback', () => {
  const teacher = 'Let us count the five colourful stars together one at a time.';
  assert.equal(looksLikeTeacherEcho('count the five colourful stars together', teacher), true);
});
