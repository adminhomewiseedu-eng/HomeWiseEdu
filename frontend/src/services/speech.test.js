import assert from 'node:assert/strict';
import { beforeEach, describe, it } from 'node:test';
import { SpeechService } from './speech.js';

const deferred = () => {
  let resolve;
  let reject;
  const promise = new Promise((res, rej) => { resolve = res; reject = rej; });
  return { promise, resolve, reject };
};

class FakeAudio {
  static instances = [];
  constructor() {
    this.playCalls = 0;
    this.pauseCalls = 0;
    this.play = () => { this.playCalls += 1; return Promise.resolve(); };
    this.pause = () => { this.pauseCalls += 1; };
    FakeAudio.instances.push(this);
  }
}

describe('SpeechService authoritative playback generation', () => {
  let getTTSAudio;
  beforeEach(() => {
    getTTSAudio = () => Promise.resolve({ data: {} });
    FakeAudio.instances = [];
  });

  it('never plays a stale TTS response after a newer request', async () => {
    const oldRequest = deferred();
    const newRequest = deferred();
    const requests = [oldRequest.promise, newRequest.promise];
    getTTSAudio = () => requests.shift();
    const service = new SpeechService({ voiceClient: { getTTSAudio }, apiBaseUrl: 'http://api.test', audioFactory: () => new FakeAudio() });

    const oldPlayback = service.playAuthoritativeAudio('old');
    const newPlayback = service.playAuthoritativeAudio('new');
    oldRequest.resolve({ data: { audio_url: '/old.mp3' } });
    await Promise.resolve();
    assert.equal(FakeAudio.instances.length, 0);

    newRequest.resolve({ data: { audio_url: '/new.mp3' } });
    await Promise.resolve();
    await Promise.resolve();
    assert.equal(FakeAudio.instances.length, 1);
    assert.equal(FakeAudio.instances[0].playCalls, 1);
    FakeAudio.instances[0].onended();
    assert.equal(await oldPlayback, false);
    assert.equal(await newPlayback, true);
  });

  it('does not deliver a stale completion callback that could reopen the microphone', async () => {
    getTTSAudio = () => Promise.resolve({ data: { audio_url: '/voice.mp3' } });
    const service = new SpeechService({ voiceClient: { getTTSAudio }, audioFactory: () => new FakeAudio() });
    let oldEndCalls = 0;
    let newEndCalls = 0;

    const oldPlayback = service.playAuthoritativeAudio('first', null, () => { oldEndCalls += 1; });
    await Promise.resolve();
    await Promise.resolve();
    const oldAudio = FakeAudio.instances[0];
    const newPlayback = service.playAuthoritativeAudio('second', null, () => { newEndCalls += 1; });
    await Promise.resolve();
    await Promise.resolve();
    const newAudio = FakeAudio.instances[1];

    oldAudio.onended();
    assert.equal(oldEndCalls, 0);
    newAudio.onended();
    assert.equal(newEndCalls, 1);
    assert.equal(await oldPlayback, false);
    assert.equal(await newPlayback, true);
  });

  it('treats a Strict Mode-style replacement as a single current narration', async () => {
    const first = deferred();
    const second = deferred();
    const requests = [first.promise, second.promise];
    getTTSAudio = () => requests.shift();
    const service = new SpeechService({ voiceClient: { getTTSAudio }, audioFactory: () => new FakeAudio() });
    service.playAuthoritativeAudio('question');
    service.cancelAllSpeech();
    const current = service.playAuthoritativeAudio('question');
    first.resolve({ data: { audio_url: '/first.mp3' } });
    second.resolve({ data: { audio_url: '/second.mp3' } });
    await Promise.resolve();
    await Promise.resolve();
    assert.equal(FakeAudio.instances.length, 1);
    FakeAudio.instances[0].onended();
    assert.equal(await current, true);
  });
});
