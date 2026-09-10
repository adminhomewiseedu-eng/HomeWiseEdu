import test from 'node:test';
import assert from 'node:assert/strict';
import { deferRealtimeCompletion, drainRealtimeCompletion } from './realtimeCompletionQueue.js';

test('defers and then processes a tutor completion instead of dropping it', () => {
  const pendingRef = { current: null };
  const completion = {
    completed: true,
    hadAudio: true,
    responseTag: 'teacher_delivery',
    transcript: 'Thank you. I heard you counted them all from 1 to 5.',
  };
  const processed = [];

  deferRealtimeCompletion(pendingRef, completion);
  assert.equal(drainRealtimeCompletion(pendingRef, false, (event) => processed.push(event)), false);
  assert.equal(drainRealtimeCompletion(pendingRef, true, (event) => processed.push(event)), true);
  assert.deepEqual(processed, [completion]);
  assert.equal(pendingRef.current, null);
});
