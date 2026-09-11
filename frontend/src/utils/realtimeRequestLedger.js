export class RealtimeRequestLedger {
  constructor() {
    this.inFlight = new Map();
  }

  reserve({ requestKey, responseTag, authoritativePhase = null, deliveryToken = null }) {
    if (!requestKey || this.inFlight.has(requestKey)) return null;
    const metadata = Object.freeze({ requestKey, responseTag, authoritativePhase, deliveryToken });
    this.inFlight.set(requestKey, metadata);
    return metadata;
  }

  release(requestKey) {
    if (requestKey) this.inFlight.delete(requestKey);
  }

  has(requestKey) {
    return this.inFlight.has(requestKey);
  }

  clear() {
    this.inFlight.clear();
  }
}
