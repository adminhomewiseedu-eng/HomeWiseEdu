const now = () => (typeof performance !== 'undefined' ? performance.now() : Date.now());

export class RealtimeClassroom {
  constructor(handlers = {}) {
    this.handlers = handlers;
    this.pc = null;
    this.dc = null;
    this.stream = null;
    this.audio = null;
    this.pendingSpeech = null;
    this.responseTranscript = '';
    this.responseHasAudio = false;
    this.nextResponseTag = null;
    this.responseTag = null;
    this.marks = {};
    this.diagnosticsEnabled = Boolean(import.meta.env?.DEV);
  }

  get connected() {
    return this.dc?.readyState === 'open' && !['closed', 'failed'].includes(this.pc?.connectionState);
  }

  mark(name) {
    this.marks[name] = now();
    if (!this.diagnosticsEnabled) return;
    if (name === 'first_audio_delta' && this.marks.speech_stopped) {
      console.info('[Realtime latency]', {
        speechEndToResponseCreatedMs: this.marks.response_created
          ? Math.round(this.marks.response_created - this.marks.speech_stopped)
          : null,
        responseCreatedToFirstAudioMs: this.marks.response_created
          ? Math.round(this.marks.first_audio_delta - this.marks.response_created)
          : null,
        speechEndToFirstAudioMs: Math.round(this.marks.first_audio_delta - this.marks.speech_stopped),
      });
    }
    this.handlers.onDiagnostic?.({ name, timestamp: this.marks[name], marks: { ...this.marks } });
  }

  send(event) {
    if (!this.connected) return false;
    this.dc.send(JSON.stringify(event));
    return true;
  }

  async connect(clientSecret) {
    if (!clientSecret) throw new Error('Missing Realtime client secret');
    this.close();
    this.pc = new RTCPeerConnection();
    this.audio = document.createElement('audio');
    this.audio.autoplay = true;
    this.audio.onplaying = () => this.mark('remote_audio_track_playing');
    this.pc.ontrack = (event) => { this.audio.srcObject = event.streams[0]; };
    const reportConnection = () => this.handlers.onConnectionState?.({
      connectionState: this.pc?.connectionState,
      iceConnectionState: this.pc?.iceConnectionState,
      signalingState: this.pc?.signalingState,
      audioTrackState: this.stream?.getAudioTracks()?.[0]?.readyState || 'unavailable',
    });
    this.pc.onconnectionstatechange = reportConnection;
    this.pc.oniceconnectionstatechange = reportConnection;
    this.pc.onsignalingstatechange = reportConnection;

    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    this.stream.getAudioTracks().forEach((track) => this.pc.addTrack(track, this.stream));

    this.dc = this.pc.createDataChannel('oai-events');
    this.dc.addEventListener('message', (event) => {
      try {
        this.handleEvent(JSON.parse(event.data));
      } catch (error) {
        this.handlers.onError?.(`Invalid Realtime event: ${error.message}`);
      }
    });
    const opened = new Promise((resolve, reject) => {
      this.dc.addEventListener('open', resolve, { once: true });
      this.dc.addEventListener('error', () => reject(new Error('Realtime data channel failed')), { once: true });
    });

    const offer = await this.pc.createOffer();
    await this.pc.setLocalDescription(offer);
    const response = await fetch('https://api.openai.com/v1/realtime/calls', {
      method: 'POST',
      body: offer.sdp,
      headers: { Authorization: `Bearer ${clientSecret}`, 'Content-Type': 'application/sdp' },
    });
    if (!response.ok) throw new Error(`Realtime connection failed (${response.status})`);
    await this.pc.setRemoteDescription({ type: 'answer', sdp: await response.text() });
    await opened;
    this.mark('session_connected');
  }

  handleEvent(event) {
    if (event.type === 'input_audio_buffer.speech_started') {
      this.mark('speech_started');
      this.mark('interruption_or_speech_start');
      if (this.pendingSpeech) {
        this.pendingSpeech.resolve(false);
        this.pendingSpeech = null;
      }
      this.handlers.onSpeechStarted?.();
      return;
    }
    if (event.type === 'input_audio_buffer.speech_stopped') {
      this.mark('speech_stopped');
      this.handlers.onSpeechStopped?.();
      return;
    }
    if (event.type === 'conversation.item.input_audio_transcription.completed') {
      const transcript = String(event.transcript || '').trim();
      if (transcript) this.handlers.onTranscript?.(transcript);
      return;
    }
    if (event.type === 'response.created') {
      this.responseTranscript = '';
      this.responseHasAudio = false;
      this.responseTag = this.nextResponseTag;
      this.nextResponseTag = null;
      this.mark('response_created');
      this.handlers.onResponseCreated?.(event.response);
      return;
    }
    if (event.type === 'response.output_audio_transcript.delta') {
      this.responseTranscript += event.delta || '';
      return;
    }
    if (event.type === 'response.output_audio_transcript.done') {
      this.responseTranscript = String(event.transcript || this.responseTranscript).trim();
      return;
    }
    if (event.type === 'response.output_audio.delta' || event.type === 'response.audio.delta') {
      if (!this.responseHasAudio) {
        this.mark('first_audio_delta');
        if (typeof requestAnimationFrame !== 'undefined') {
          requestAnimationFrame(() => this.mark('first_audio_playback'));
        }
      }
      this.responseHasAudio = true;
      this.handlers.onTutorSpeaking?.();
      return;
    }
    if (event.type === 'response.done') {
      this.mark(event.response?.status === 'cancelled' ? 'response_cancelled' : 'response_completed');
      const functionCalls = (event.response?.output || []).filter((item) => item.type === 'function_call');
      if (functionCalls.length) {
        functionCalls.forEach((call) => this.handlers.onToolCall?.({
          name: call.name,
          callId: call.call_id,
          arguments: call.arguments || '{}',
        }));
        return;
      }
      const completed = event.response?.status === 'completed';
      if (this.pendingSpeech) {
        this.pendingSpeech.resolve(completed);
        this.pendingSpeech = null;
      }
      this.handlers.onTutorDone?.({
        completed,
        status: event.response?.status,
        transcript: this.responseTranscript.trim(),
        hadAudio: this.responseHasAudio,
        responseTag: this.responseTag,
      });
      return;
    }
    if (event.type === 'error') {
      this.handlers.onError?.(event.error?.message || 'Realtime session error');
    }
  }

  updateInstructions(instructions) {
    return this.send({ type: 'session.update', session: { instructions } });
  }

  createResponse(instructions = null, responseTag = null) {
    const response = { output_modalities: ['audio'] };
    if (instructions) response.instructions = instructions;
    this.nextResponseTag = responseTag;
    return this.send({ type: 'response.create', response });
  }

  sendFunctionOutput(callId, output, instructions = null, responseTag = 'academic_feedback') {
    if (!this.send({
      type: 'conversation.item.create',
      item: { type: 'function_call_output', call_id: callId, output: JSON.stringify(output) },
    })) return false;
    return this.createResponse(instructions, responseTag);
  }

  speak(text) {
    if (!this.connected) return Promise.resolve(false);
    if (this.pendingSpeech) this.pendingSpeech.resolve(false);
    return new Promise((resolve) => {
      this.pendingSpeech = { resolve };
      this.createResponse(`Speak the following teacher message exactly:\n\n${text}`);
    });
  }

  setMuted(muted) {
    this.stream?.getAudioTracks().forEach((track) => { track.enabled = !muted; });
  }

  cancelResponse() {
    const sent = this.send({ type: 'response.cancel' });
    if (sent) this.mark('interruption_cancellation');
    if (this.pendingSpeech) this.pendingSpeech.resolve(false);
    this.pendingSpeech = null;
  }

  close() {
    if (this.pendingSpeech) this.pendingSpeech.resolve(false);
    this.pendingSpeech = null;
    this.dc?.close();
    this.pc?.close();
    this.stream?.getTracks().forEach((track) => track.stop());
    if (this.audio) this.audio.srcObject = null;
    this.dc = null;
    this.pc = null;
    this.stream = null;
    this.audio = null;
  }
}
