import assert from 'node:assert/strict';
import { it } from 'node:test';
import { adaptiveSilenceMs, isStableBargeCandidate } from './voiceTurn.js';

it('allows a longer pause when a learner is visibly hesitating', () => {
  assert.equal(adaptiveSilenceMs('I think maybe'), 3800);
  assert.equal(adaptiveSilenceMs('The answer is five.'), 2200);
  assert.equal(adaptiveSilenceMs('five'), 3200);
});

it('accepts a growing stable interruption transcript', () => {
  assert.equal(isStableBargeCandidate('what is', 'what is the topic'), true);
  assert.equal(isStableBargeCandidate('what is', 'teacher audio echo'), false);
});
