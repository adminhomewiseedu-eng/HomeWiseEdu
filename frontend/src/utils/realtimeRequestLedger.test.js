import assert from 'node:assert/strict';
import test from 'node:test';
import { RealtimeRequestLedger } from './realtimeRequestLedger.js';

test('guards only an in-flight authoritative request and permits reuse after completion', () => {
  const ledger = new RealtimeRequestLedger();
  const request = {
    requestKey: 'WE1->WE2:teacher_delivery',
    responseTag: 'teacher_delivery',
    authoritativePhase: 'WORKED_EXAMPLE_2',
    deliveryToken: 'token-we2',
  };
  assert.deepEqual(ledger.reserve(request), request);
  assert.equal(ledger.reserve(request), null);
  ledger.release(request.requestKey);
  assert.deepEqual(ledger.reserve(request), request);
});

test('releases request keys after cancellation, interruption, or send failure', () => {
  const ledger = new RealtimeRequestLedger();
  for (const reason of ['cancellation', 'interruption', 'failure']) {
    const requestKey = `WE2->WE3:${reason}`;
    assert.ok(ledger.reserve({ requestKey, responseTag: 'teacher_delivery' }));
    ledger.release(requestKey);
    assert.equal(ledger.has(requestKey), false);
  }
});
