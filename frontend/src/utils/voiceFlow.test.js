import assert from 'node:assert/strict';
import { it } from 'node:test';
import { advanceAfterFeedback } from './voiceFlow.js';

it('waits for feedback playback completion before advancing the quiz', async () => {
  let finishPlayback;
  const playFeedback = () => new Promise((resolve) => { finishPlayback = resolve; });
  let advances = 0;
  const advance = () => { advances += 1; };
  const pending = advanceAfterFeedback(playFeedback, 'Correct!', advance);
  await Promise.resolve();
  assert.equal(advances, 0);
  finishPlayback(true);
  await pending;
  assert.equal(advances, 1);
});

it('does not advance after cancelled feedback playback', async () => {
  let advances = 0;
  const advance = () => { advances += 1; };
  await advanceAfterFeedback(() => Promise.resolve(false), 'Cancelled', advance);
  assert.equal(advances, 0);
});
