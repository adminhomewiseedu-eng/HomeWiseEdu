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
