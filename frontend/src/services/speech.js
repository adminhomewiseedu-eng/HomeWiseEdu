// Web Speech API and Authoritative Audio Coordinator for Ms. Ade (ElevenLabs & OpenAI TTS)
import { voiceAPI, API_BASE_URL } from './api.js';

export class SpeechService {
  constructor({ voiceClient = voiceAPI, apiBaseUrl = API_BASE_URL, audioFactory = () => new Audio() } = {}) {
    this.voiceClient = voiceClient;
    this.apiBaseUrl = apiBaseUrl;
    this.audioFactory = audioFactory;
    this.synth = typeof window !== 'undefined' ? window.speechSynthesis : null;
    this.voice = null;
    this.isSpeaking = false;
    this.activeAudio = null;
    this.playbackGeneration = 0;
    this.ttsAbortController = null;
    this.activePlaybackResolve = null;

    // Speech Recognition
    const SpeechRecognition = typeof window !== 'undefined'
      ? (window.SpeechRecognition || window.webkitSpeechRecognition)
      : null;

    this.recognition = SpeechRecognition ? new SpeechRecognition() : null;
    this.isListening = false;

    if (this.synth) {
      this.initVoice();
      if (this.synth.onvoiceschanged !== undefined) {
        this.synth.onvoiceschanged = () => this.initVoice();
      }
    }
  }

  initVoice() {
    if (!this.synth) return;
    const voices = this.synth.getVoices();
    const preferred = voices.find(
      (v) =>
        v.lang.startsWith('en') &&
        (v.name.includes('Female') ||
          v.name.includes('Natural') ||
          v.name.includes('Google') ||
          v.name.includes('Samantha') ||
          v.name.includes('Victoria'))
    );
    this.voice = preferred || voices.find((v) => v.lang.startsWith('en')) || voices[0];
  }

  // Cancel ALL speech across both server Audio and browser SpeechSynthesis
  cancelAllSpeech() {
    this.playbackGeneration += 1;
    if (this.ttsAbortController) {
      this.ttsAbortController.abort();
      this.ttsAbortController = null;
    }
    if (this.synth) {
      try {
        this.synth.cancel();
      } catch (e) {}
    }
    if (this.activeAudio) {
      try {
        this.activeAudio.pause();
        this.activeAudio.currentTime = 0;
        this.activeAudio.src = '';
      } catch (e) {}
      this.activeAudio = null;
    }
    if (this.activePlaybackResolve) {
      this.activePlaybackResolve(false);
      this.activePlaybackResolve = null;
    }
    this.isSpeaking = false;
  }

  // Browser speech synthesis fallback ONLY
  speak(text, onStart, onEnd) {
    this.cancelAllSpeech();
    const token = this.playbackGeneration;
    return this._speakFallback(text, onStart, onEnd, token);
  }

  _speakFallback(text, onStart, onEnd, token) {
    if (!this.synth) {
      if (token === this.playbackGeneration && onEnd) onEnd(token);
      return Promise.resolve(token === this.playbackGeneration);
    }

    const cleanText = text.replace(/[\u{1F600}-\u{1F64F}|\u{1F300}-\u{1F5FF}|\u{1F680}-\u{1F6FF}|\u{1F1E0}-\u{1F1FF}|\u{2600}-\u{26FF}|\u{2700}-\u{27BF}]/gu, '');
    const utterance = new SpeechSynthesisUtterance(cleanText);
    
    if (this.voice) {
      utterance.voice = this.voice;
    }
    utterance.rate = 0.95; // Friendly, clear pace for children
    utterance.pitch = 1.05; // Warm, encouraging tone

    return new Promise((resolve) => {
      this.activePlaybackResolve = resolve;
      utterance.onstart = () => {
        if (token !== this.playbackGeneration) return;
      this.isSpeaking = true;
        if (onStart) onStart(token);
      };

      const finish = () => {
        const isCurrent = token === this.playbackGeneration;
        if (isCurrent) {
      this.isSpeaking = false;
          this.activePlaybackResolve = null;
          if (onEnd) onEnd(token);
        }
        resolve(isCurrent);
      };
      utterance.onend = finish;
      utterance.onerror = finish;

    this.synth.speak(utterance);
    });
  }

  stop() {
    this.cancelAllSpeech();
  }

  // Play authoritative teacher voice (Priority: 1. ElevenLabs / Backend TTS -> 2. Browser TTS Fallback)
  async playAuthoritativeAudio(textToSpeak, onStart, onEnd) {
    if (!textToSpeak) {
      if (onEnd) onEnd(this.playbackGeneration);
      return false;
    }

    this.cancelAllSpeech();
    const token = this.playbackGeneration;
    const controller = new AbortController();
    this.ttsAbortController = controller;

    let shouldFallback = true;

    try {
      const res = await this.voiceClient.getTTSAudio(textToSpeak, null, controller.signal);
      if (token !== this.playbackGeneration || controller.signal.aborted) return false;
      const audioUrl = res.data?.audio_url;

      if (audioUrl) {
        const fullUrl = audioUrl.startsWith('http') ? audioUrl : `${this.apiBaseUrl}${audioUrl}`;
        const audio = this.audioFactory();
        this.activeAudio = audio;
        audio.src = fullUrl;

        shouldFallback = false;
        const completed = await new Promise((resolve, reject) => {
          this.activePlaybackResolve = resolve;
          audio.onended = () => {
            const isCurrent = token === this.playbackGeneration;
            if (isCurrent) {
              this.activeAudio = null;
              this.activePlaybackResolve = null;
              this.isSpeaking = false;
              if (onEnd) onEnd(token);
            }
            resolve(isCurrent);
          };
          audio.onerror = (e) => {
            this.activePlaybackResolve = null;
            reject(e);
          };

          const playPromise = audio.play();
          if (playPromise !== undefined) {
            playPromise.then(() => {
              if (token !== this.playbackGeneration) {
                audio.pause();
                resolve(false);
                return;
              }
              this.isSpeaking = true;
              if (onStart) onStart(token);
            }).catch((err) => {
              if (err.name === 'AbortError' || token !== this.playbackGeneration) {
                resolve(false);
              } else {
                reject(err);
              }
            });
          }
        });
        return completed;
      }
    } catch (err) {
      if (token !== this.playbackGeneration || controller.signal.aborted || err?.code === 'ERR_CANCELED') {
        return false;
      }
      shouldFallback = true;
      console.warn('Backend TTS notice, falling back to browser synthesis:', err);
    } finally {
      if (this.ttsAbortController === controller) this.ttsAbortController = null;
    }

    if (shouldFallback && token === this.playbackGeneration) {
      return this._speakFallback(textToSpeak, onStart, onEnd, token);
    }
    return false;
  }

  // Voice Input (Microphone Recognition)
  isRecognitionSupported() {
    return typeof window !== 'undefined' && !!(window.SpeechRecognition || window.webkitSpeechRecognition);
  }

  startListening({ onResult, onError, onEnd, onStart, continuous = true, interimResults = true }) {
    const SpeechRecognition = typeof window !== 'undefined'
      ? (window.SpeechRecognition || window.webkitSpeechRecognition)
      : null;

    if (!SpeechRecognition) {
      if (onError) onError('Speech recognition is not supported in this browser.');
      return;
    }

    this.stopListening();

    try {
      this.recognition = new SpeechRecognition();
      this.recognition.continuous = continuous;
      this.recognition.interimResults = interimResults;
      this.recognition.lang = 'en-US';

      this.recognition.onstart = () => {
        this.isListening = true;
        if (onStart) onStart();
      };

      this.recognition.onresult = (event) => {
        let fullTranscript = '';
        let latestTranscript = '';
        let confidence = 0;
        let isFinal = false;
        for (let i = 0; i < event.results.length; i++) {
          fullTranscript += event.results[i][0].transcript + ' ';
          if (i >= event.resultIndex) latestTranscript += event.results[i][0].transcript + ' ';
          confidence = Math.max(confidence, event.results[i][0].confidence || 0);
          isFinal = isFinal || event.results[i].isFinal;
        }
        if (onResult) onResult(fullTranscript.trim(), { confidence, isFinal, latestTranscript: latestTranscript.trim() });
      };

      this.recognition.onerror = (event) => {
        if (onError) onError(event.error);
      };

      this.recognition.onend = () => {
        this.isListening = false;
        if (onEnd) onEnd();
      };

      this.recognition.start();
    } catch (e) {
      this.isListening = false;
      if (onError) onError(e);
    }
  }

  stopListening() {
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch (e) {}
      this.recognition = null;
    }
    this.isListening = false;
  }
}

export const speechService = new SpeechService();
