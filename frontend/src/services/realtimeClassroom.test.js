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
  assert.equal(realtime.responseTag, 'academic_feedback');
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
