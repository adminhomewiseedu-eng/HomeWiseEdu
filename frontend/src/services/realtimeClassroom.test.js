import assert from 'node:assert/strict';
import { it } from 'node:test';
import { RealtimeClassroom } from './realtimeClassroom.js';

it('delivers completed microphone transcripts to the application', () => {
  let heard = '';
  const realtime = new RealtimeClassroom({ onTranscript: (text) => { heard = text; } });
  realtime.handleEvent({
    type: 'conversation.item.input_audio_transcription.completed',
    transcript: '  I think the answer is five.  ',
  });
  assert.equal(heard, 'I think the answer is five.');
});

it('treats server VAD speech-start as a native tutor interruption', async () => {
  let interrupted = 0;
  const realtime = new RealtimeClassroom({ onSpeechStarted: () => { interrupted += 1; } });
  let completed;
  const pending = new Promise((resolve) => { completed = resolve; });
  realtime.pendingSpeech = { resolve: completed };
  realtime.handleEvent({ type: 'input_audio_buffer.speech_started' });
  assert.equal(await pending, false);
  assert.equal(interrupted, 1);
  assert.equal(realtime.pendingSpeech, null);
});

it('requests audio that is constrained to the backend-approved teacher text', async () => {
  let sent;
  const realtime = new RealtimeClassroom();
  realtime.pc = { connectionState: 'connected' };
  realtime.dc = { readyState: 'open', send: (payload) => { sent = JSON.parse(payload); } };
  const pending = realtime.speak('There are five stars.');
  assert.equal(sent.type, 'response.create');
  assert.match(sent.response.instructions, /There are five stars\./);
  realtime.handleEvent({ type: 'response.done', response: { status: 'completed' } });
  assert.equal(await pending, true);
});

it('sends a valid typed session update for authoritative phase instructions', () => {
  let sent;
  const realtime = new RealtimeClassroom();
  realtime.pc = { connectionState: 'connected' };
  realtime.dc = { readyState: 'open', send: (payload) => { sent = JSON.parse(payload); } };
  realtime.updateInstructions('Authoritative phase: WORKED_EXAMPLE_2.');
  assert.deepEqual(sent, {
    type: 'session.update',
    session: {
      type: 'realtime',
      instructions: 'Authoritative phase: WORKED_EXAMPLE_2.',
    },
  });
});

it('delivers realtime function calls without treating them as completed speech', () => {
  let toolCall;
  let tutorDone = 0;
  const realtime = new RealtimeClassroom({
    onToolCall: (call) => { toolCall = call; },
    onTutorDone: () => { tutorDone += 1; },
  });
  realtime.handleEvent({
    type: 'response.done',
    response: {
      status: 'completed',
      output: [{
        type: 'function_call',
        name: 'submit_academic_response',
        call_id: 'call-1',
        arguments: '{"student_response":"five"}',
      }],
    },
  });
  assert.equal(toolCall.name, 'submit_academic_response');
  assert.equal(toolCall.callId, 'call-1');
  assert.equal(tutorDone, 0);
});

it('returns tool output to the same realtime conversation and starts tagged audio', () => {
  const sent = [];
  const realtime = new RealtimeClassroom();
  realtime.pc = { connectionState: 'connected' };
  realtime.dc = { readyState: 'open', send: (payload) => sent.push(JSON.parse(payload)) };
  realtime.sendFunctionOutput('call-2', { result: 'correct' }, 'Continue.', 'academic_feedback');
  assert.equal(sent[0].type, 'conversation.item.create');
  assert.equal(sent[0].item.type, 'function_call_output');
  assert.equal(sent[1].type, 'response.create');
  realtime.handleEvent({ type: 'response.created', response: { id: 'response-2' } });
  realtime.handleEvent({ type: 'response.done', response: { id: 'response-2', status: 'completed', output: [] } });
});

it('stops remote teacher audio when the realtime classroom closes', () => {
  let paused = 0;
  const realtime = new RealtimeClassroom();
  realtime.audio = { pause: () => { paused += 1; }, srcObject: {} };
  realtime.close();
  assert.equal(paused, 1);
  assert.equal(realtime.audio, null);
});

it('waits for the WebRTC output buffer to drain before completing teacher delivery', () => {
  const completed = [];
  const realtime = new RealtimeClassroom({ onTutorDone: (event) => completed.push(event) });
  realtime.handleEvent({ type: 'response.created', response: { id: 'response-a' } });
  realtime.handleEvent({ type: 'response.output_audio.delta', response_id: 'response-a', delta: 'audio' });
  realtime.handleEvent({ type: 'response.output_audio_transcript.done', response_id: 'response-a', transcript: 'The complete example.' });
  realtime.handleEvent({ type: 'response.done', response: { id: 'response-a', status: 'completed', output: [] } });
  assert.equal(completed.length, 0);
  realtime.handleEvent({ type: 'output_audio_buffer.stopped', response_id: 'response-a' });
  assert.equal(completed.length, 1);
  assert.equal(completed[0].transcript, 'The complete example.');
});

it('deduplicates repeated response and audio completion events', () => {
  let completions = 0;
  const realtime = new RealtimeClassroom({ onTutorDone: () => { completions += 1; } });
  realtime.handleEvent({ type: 'response.created', response: { id: 'response-b' } });
  realtime.handleEvent({ type: 'response.output_audio.delta', response_id: 'response-b', delta: 'audio' });
  const done = { type: 'response.done', response: { id: 'response-b', status: 'completed', output: [] } };
  realtime.handleEvent(done);
  realtime.handleEvent(done);
  realtime.handleEvent({ type: 'output_audio_buffer.stopped', response_id: 'response-b' });
  realtime.handleEvent({ type: 'output_audio_buffer.stopped', response_id: 'response-b' });
  assert.equal(completions, 1);
});

it('binds immutable authority metadata to the exact explicit response', () => {
  const sent = [];
  const completed = [];
  const realtime = new RealtimeClassroom({ onTutorDone: (event) => completed.push(event) });
  realtime.pc = { connectionState: 'connected' };
  realtime.dc = { readyState: 'open', send: (payload) => sent.push(JSON.parse(payload)) };
  const authority = Object.freeze({
    requestKey: 'TEACHING->WORKED_EXAMPLE_1:teacher_delivery',
    responseTag: 'teacher_delivery',
    authoritativePhase: 'WORKED_EXAMPLE_1',
    deliveryToken: 'token-we1',
  });
  assert.equal(realtime.createResponse('Teach example one.', 'teacher_delivery', authority), true);
  const metadata = sent[0].response.metadata;
  realtime.handleEvent({ type: 'response.created', response: { id: 'explicit-1', metadata } });
  realtime.handleEvent({ type: 'response.output_audio.delta', response_id: 'explicit-1', delta: 'audio' });
  realtime.handleEvent({ type: 'response.done', response: { id: 'explicit-1', status: 'completed', output: [] } });
  realtime.handleEvent({ type: 'output_audio_buffer.stopped', response_id: 'explicit-1' });
  assert.deepEqual(completed[0].responseMetadata, authority);
  assert.equal(Object.isFrozen(completed[0].responseMetadata), true);
});

it('isolates an automatic VAD response arriving beside an explicit teacher response', () => {
  const sent = [];
  const completed = [];
  const realtime = new RealtimeClassroom({ onTutorDone: (event) => completed.push(event) });
  realtime.pc = { connectionState: 'connected' };
  realtime.dc = { readyState: 'open', send: (payload) => sent.push(JSON.parse(payload)) };
  const authority = { requestKey: 'WE1->WE2', responseTag: 'teacher_delivery', authoritativePhase: 'WORKED_EXAMPLE_2', deliveryToken: 'token-we2' };
  realtime.createResponse('Teach WE2.', 'teacher_delivery', authority);
  realtime.handleEvent({ type: 'response.created', response: { id: 'vad-auto', metadata: null } });
  realtime.handleEvent({ type: 'response.done', response: { id: 'vad-auto', status: 'completed', output: [] } });
  realtime.handleEvent({ type: 'response.created', response: { id: 'explicit-2', metadata: sent[0].response.metadata } });
  realtime.handleEvent({ type: 'response.done', response: { id: 'explicit-2', status: 'completed', output: [] } });
  assert.equal(completed[0].responseMetadata, null);
  assert.equal(completed[1].responseMetadata.deliveryToken, 'token-we2');
});

it('reconciles a delayed playback stop whose response id is absent when only one response awaits drain', () => {
  const completed = [];
  const realtime = new RealtimeClassroom({ onTutorDone: (event) => completed.push(event) });
  realtime.handleEvent({ type: 'response.created', response: { id: 'drain-1' } });
  realtime.handleEvent({ type: 'response.output_audio.delta', response_id: 'drain-1', delta: 'audio' });
  realtime.handleEvent({ type: 'response.done', response: { id: 'drain-1', status: 'completed', output: [] } });
  realtime.handleEvent({ type: 'output_audio_buffer.stopped' });
  assert.equal(completed.length, 1);
  assert.equal(completed[0].responseId, 'drain-1');
});

it('marks interrupted authoritative responses incomplete and releases their request', () => {
  const interrupted = [];
  const completed = [];
  const realtime = new RealtimeClassroom({
    onResponseInterrupted: (metadata) => interrupted.push(metadata.requestKey),
    onTutorDone: (event) => completed.push(event),
  });
  realtime.handleEvent({ type: 'response.created', response: { id: 'we3', metadata: {
    hwe_request_key: 'WE2->WE3', hwe_response_tag: 'teacher_delivery',
    hwe_authoritative_phase: 'WORKED_EXAMPLE_3', hwe_delivery_token: 'token-we3',
  } } });
  realtime.handleEvent({ type: 'response.output_audio.delta', response_id: 'we3', delta: 'audio' });
  realtime.handleEvent({ type: 'input_audio_buffer.speech_started' });
  realtime.handleEvent({ type: 'response.done', response: { id: 'we3', status: 'cancelled', output: [] } });
  assert.deepEqual(interrupted, ['WE2->WE3']);
  assert.equal(completed[0].completed, false);
});

it('reports failed explicit response requests so their keys can be reused', () => {
  const failed = [];
  let wire;
  const realtime = new RealtimeClassroom({ onResponseFailed: (metadata) => failed.push(metadata.requestKey) });
  realtime.pc = { connectionState: 'connected' };
  realtime.dc = { readyState: 'open', send: (payload) => { wire = JSON.parse(payload); } };
  realtime.createResponse('Teach.', 'teacher_delivery', {
    requestKey: 'WE3->CHECK', responseTag: 'teacher_delivery', authoritativePhase: 'UNDERSTANDING_CHECK', deliveryToken: 'token-check',
  });
  realtime.handleEvent({ type: 'error', error: { event_id: wire.event_id, message: 'response failed' } });
  assert.deepEqual(failed, ['WE3->CHECK']);
});
