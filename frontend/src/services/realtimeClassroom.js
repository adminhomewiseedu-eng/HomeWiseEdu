export class RealtimeClassroom {
  constructor(handlers = {}) {
    this.handlers = handlers;
    this.pc = null;
    this.dc = null;
    this.stream = null;
    this.audio = null;
    this.pendingSpeech = null;
  }

  get connected() {
    return this.dc?.readyState === 'open' && this.pc?.connectionState !== 'closed';
  }

  async connect(clientSecret) {
    if (!clientSecret) throw new Error('Missing Realtime client secret');
    this.close();
    this.pc = new RTCPeerConnection();
    this.audio = document.createElement('audio');
    this.audio.autoplay = true;
    this.pc.ontrack = (event) => { this.audio.srcObject = event.streams[0]; };
    this.pc.onconnectionstatechange = () => this.handlers.onConnectionState?.(this.pc?.connectionState);

    this.stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    this.stream.getAudioTracks().forEach((track) => this.pc.addTrack(track, this.stream));

    this.dc = this.pc.createDataChannel('oai-events');
    this.dc.addEventListener('message', (event) => this.handleEvent(JSON.parse(event.data)));
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
  }

  handleEvent(event) {
    if (event.type === 'input_audio_buffer.speech_started') {
      if (this.pendingSpeech) {
        this.pendingSpeech.resolve(false);
        this.pendingSpeech = null;
      }
      this.handlers.onSpeechStarted?.();
    } else if (event.type === 'input_audio_buffer.speech_stopped') {
      this.handlers.onSpeechStopped?.();
    } else if (event.type === 'conversation.item.input_audio_transcription.completed') {
      const transcript = String(event.transcript || '').trim();
      if (transcript) this.handlers.onTranscript?.(transcript);
    } else if (event.type === 'response.output_audio.delta' || event.type === 'response.audio.delta') {
      this.handlers.onTutorSpeaking?.();
    } else if (event.type === 'response.done') {
      const completed = event.response?.status === 'completed';
      if (this.pendingSpeech) {
        this.pendingSpeech.resolve(completed);
        this.pendingSpeech = null;
      }
      this.handlers.onTutorDone?.(completed);
    } else if (event.type === 'error') {
      this.handlers.onError?.(event.error?.message || 'Realtime session error');
    }
  }

  speak(text) {
    if (!this.connected) return Promise.resolve(false);
    if (this.pendingSpeech) this.pendingSpeech.resolve(false);
    return new Promise((resolve) => {
      this.pendingSpeech = { resolve };
      this.dc.send(JSON.stringify({
        type: 'response.create',
        response: {
          output_modalities: ['audio'],
          instructions: `Speak the following teacher message exactly. Do not add, remove, answer, or paraphrase anything:\n\n${text}`,
        },
      }));
    });
  }

  setMuted(muted) {
    this.stream?.getAudioTracks().forEach((track) => { track.enabled = !muted; });
  }

  cancelResponse() {
    if (this.connected) this.dc.send(JSON.stringify({ type: 'response.cancel' }));
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
