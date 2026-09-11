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
    this.responseStates = new Map();
    this.completedResponseIds = new Set();
    this.pendingRequestEvents = new Map();
    this.requestSequence = 0;
    this.marks = {};
    this.diagnosticsEnabled = Boolean(import.meta.env?.DEV);
  }

  get connected() {
    return this.dc?.readyState === 'open' && !['closed', 'failed'].includes(this.pc?.connectionState);
  }

  mark(name) {
    this.marks[name] = now();
    if (!this.diagnosticsEnabled) return;
    if (['response_created', 'response_completed', 'response_cancelled', 'response_audio_done',
      'output_audio_buffer_stopped', 'output_audio_buffer_cleared', 'interruption_cancellation'].includes(name)) {
      console.info('[Realtime progression]', { event: name, timestamp: Math.round(this.marks[name]) });
    }
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
      audio: {
        echoCancellation: true,
        // Realtime applies its own far-field noise reduction. Applying the
        // browser filter as well can erase quiet or developing voices.
        noiseSuppression: false,
        autoGainControl: true,
        channelCount: 1,
      },
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
      for (const state of this.responseStates.values()) {
        if (state.metadata?.requestKey && !state.settled) {
          state.interrupted = true;
          this.handlers.onResponseInterrupted?.(state.metadata);
        }
      }
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
      const responseId = event.response?.id || null;
      this.responseTranscript = '';
      this.responseHasAudio = false;
      const wireMetadata = event.response?.metadata || {};
      const metadata = (wireMetadata.hwe_request_key || wireMetadata.hwe_response_tag) ? Object.freeze({
        requestKey: wireMetadata.hwe_request_key || null,
        responseTag: wireMetadata.hwe_response_tag || null,
        authoritativePhase: wireMetadata.hwe_authoritative_phase || null,
        deliveryToken: wireMetadata.hwe_delivery_token || null,
      }) : null;
      if (responseId) this.responseStates.set(responseId, {
        transcript: '', hadAudio: false, metadata,
        response: event.response, responseDone: false, audioStopped: false,
        interrupted: false, settled: false,
      });
      if (metadata?.requestKey) {
        for (const [eventId, pending] of this.pendingRequestEvents.entries()) {
          if (pending.requestKey === metadata.requestKey) this.pendingRequestEvents.delete(eventId);
        }
      }
      this.mark('response_created');
      this.handlers.onResponseCreated?.(event.response);
      return;
    }
    if (event.type === 'response.output_audio_transcript.delta') {
      this.responseTranscript += event.delta || '';
      const state = this.responseStates.get(event.response_id);
      if (state) state.transcript += event.delta || '';
      return;
    }
    if (event.type === 'response.output_audio_transcript.done') {
      this.responseTranscript = String(event.transcript || this.responseTranscript).trim();
      const state = this.responseStates.get(event.response_id);
      if (state) state.transcript = this.responseTranscript;
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
      const state = this.responseStates.get(event.response_id);
      if (state) state.hadAudio = true;
      this.handlers.onTutorSpeaking?.();
      return;
    }
    if (event.type === 'response.output_audio.done' || event.type === 'response.audio.done') {
      this.mark('response_audio_done');
      return;
    }
    if (event.type === 'output_audio_buffer.stopped') {
      this.mark('output_audio_buffer_stopped');
      let state = this.responseStates.get(event.response_id);
      let responseId = event.response_id;
      if (!state) {
        const awaitingDrain = [...this.responseStates.entries()].filter(([, candidate]) => (
          candidate.responseDone && candidate.hadAudio && !candidate.audioStopped
        ));
        if (awaitingDrain.length === 1) [responseId, state] = awaitingDrain[0];
      }
      if (state) {
        state.audioStopped = true;
        this.finalizeResponse(responseId);
      }
      return;
    }
    if (event.type === 'output_audio_buffer.cleared') {
      this.mark('output_audio_buffer_cleared');
      for (const [responseId, state] of this.responseStates.entries()) {
        if (!state.settled && state.hadAudio && !state.audioStopped) {
          state.interrupted = true;
          state.audioStopped = true;
          this.handlers.onResponseInterrupted?.(state.metadata);
          this.finalizeResponse(responseId);
        }
      }
      return;
    }
    if (event.type === 'response.done') {
      this.mark(event.response?.status === 'cancelled' ? 'response_cancelled' : 'response_completed');
      const responseId = event.response?.id || null;
      if (responseId && this.completedResponseIds.has(responseId)) return;
      const functionCalls = (event.response?.output || []).filter((item) => item.type === 'function_call');
      if (functionCalls.length) {
        if (responseId) this.completedResponseIds.add(responseId);
        functionCalls.forEach((call) => this.handlers.onToolCall?.({
          name: call.name,
          callId: call.call_id,
          arguments: call.arguments || '{}',
        }));
        return;
      }
      const state = responseId ? this.responseStates.get(responseId) : null;
      if (state) {
        state.response = event.response;
        state.responseDone = true;
        this.finalizeResponse(responseId);
      } else {
        this.emitTutorDone(responseId, event.response, {
          transcript: this.responseTranscript, hadAudio: this.responseHasAudio,
          metadata: null, audioStopped: false, interrupted: false, settled: false,
        });
      }
      return;
    }
    if (event.type === 'error') {
      const failed = this.pendingRequestEvents.get(event.error?.event_id);
      if (failed) {
        this.pendingRequestEvents.delete(event.error.event_id);
        this.handlers.onResponseFailed?.(failed);
      }
      this.handlers.onError?.(event.error?.message || 'Realtime session error');
    }
  }

  finalizeResponse(responseId) {
    const state = this.responseStates.get(responseId);
    if (!state?.responseDone) return;
    const completed = state.response?.status === 'completed';
    if (completed && state.hadAudio && !state.audioStopped) return;
    this.emitTutorDone(responseId, state.response, state);
    this.responseStates.delete(responseId);
  }

  emitTutorDone(responseId, response, state) {
    if (responseId && this.completedResponseIds.has(responseId)) return;
    if (responseId) this.completedResponseIds.add(responseId);
    state.settled = true;
    const completed = response?.status === 'completed' && !state.interrupted;
    if (this.pendingSpeech) {
      this.pendingSpeech.resolve(completed);
      this.pendingSpeech = null;
    }
    this.handlers.onTutorDone?.({
      completed,
      status: response?.status,
      transcript: String(state.transcript || '').trim(),
      hadAudio: Boolean(state.hadAudio),
      responseTag: state.metadata?.responseTag || null,
      responseMetadata: state.metadata || null,
      responseId,
    });
  }

  updateInstructions(instructions) {
    return this.send({ type: 'session.update', session: { type: 'realtime', instructions } });
  }

  createResponse(instructions = null, responseTag = null, requestMetadata = null) {
    if (requestMetadata?.requestKey) {
      const authoritativeActive = [...this.responseStates.values()].some((state) => (
        state.metadata?.deliveryToken && !state.settled
      ));
      const authoritativePending = [...this.pendingRequestEvents.values()].some((metadata) => metadata.deliveryToken);
      if (authoritativeActive || authoritativePending) return false;
    }
    const response = { output_modalities: ['audio'] };
    if (instructions) response.instructions = instructions;
    if (requestMetadata?.requestKey) {
      response.metadata = {
        hwe_request_key: requestMetadata.requestKey,
        hwe_response_tag: requestMetadata.responseTag || responseTag || '',
        hwe_authoritative_phase: requestMetadata.authoritativePhase || '',
        hwe_delivery_token: requestMetadata.deliveryToken || '',
      };
    } else if (responseTag) {
      response.metadata = { hwe_response_tag: responseTag };
    }
    const eventId = `hwe_response_${++this.requestSequence}`;
    if (requestMetadata?.requestKey) this.pendingRequestEvents.set(eventId, requestMetadata);
    const sent = this.send({ event_id: eventId, type: 'response.create', response });
    if (!sent) this.pendingRequestEvents.delete(eventId);
    return sent;
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
    for (const state of this.responseStates.values()) {
      if (state.metadata?.requestKey && !state.settled) {
        state.interrupted = true;
        this.handlers.onResponseInterrupted?.(state.metadata);
      }
    }
    if (this.pendingSpeech) this.pendingSpeech.resolve(false);
    this.pendingSpeech = null;
  }

  close() {
    if (this.pendingSpeech) this.pendingSpeech.resolve(false);
    this.pendingSpeech = null;
    this.dc?.close();
    this.pc?.close();
    this.stream?.getTracks().forEach((track) => track.stop());
    if (this.audio) {
      this.audio.pause();
      this.audio.srcObject = null;
    }
    this.dc = null;
    this.responseStates.clear();
    this.completedResponseIds.clear();
    for (const metadata of this.pendingRequestEvents.values()) {
      this.handlers.onResponseFailed?.(metadata);
    }
    this.pendingRequestEvents.clear();
    this.pc = null;
    this.stream = null;
    this.audio = null;
  }
}
