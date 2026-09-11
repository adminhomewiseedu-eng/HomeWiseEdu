import assert from 'node:assert/strict';
import test from 'node:test';
import { preserveRealtimeTrace } from './diagnosticRouting.js';

test('preserves opt-in realtime tracing through dashboard lesson navigation', () => {
  assert.equal(preserveRealtimeTrace('/student', '?realtimeTrace=1'), '/student?realtimeTrace=1');
  assert.equal(preserveRealtimeTrace('/lesson', '?realtimeTrace=1'), '/lesson?realtimeTrace=1');
});

test('does not enable tracing for ordinary users', () => {
  assert.equal(preserveRealtimeTrace('/lesson', ''), '/lesson');
  assert.equal(preserveRealtimeTrace('/lesson?view=notes', '?realtimeTrace=0'), '/lesson?view=notes');
});
