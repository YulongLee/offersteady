class OfferSteadyPcmCaptureProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this.batchSize = 1024;
    this.batch = new Float32Array(this.batchSize);
    this.batchOffset = 0;
    this.callbackCount = 0;
    this.postMessageCount = 0;
    this.allocationCount = 1;
  }

  process(inputs, outputs) {
    this.callbackCount += 1;
    const input = inputs[0]?.[0];
    const output = outputs[0]?.[0];
    if (output) output.fill(0);
    if (input && input.length > 0) {
      let inputOffset = 0;
      while (inputOffset < input.length) {
        const writable = Math.min(this.batchSize - this.batchOffset, input.length - inputOffset);
        this.batch.set(input.subarray(inputOffset, inputOffset + writable), this.batchOffset);
        this.batchOffset += writable;
        inputOffset += writable;
        if (this.batchOffset === this.batchSize) {
          const completed = this.batch;
          this.batch = new Float32Array(this.batchSize);
          this.allocationCount += 1;
          this.batchOffset = 0;
          this.postMessageCount += 1;
          this.port.postMessage({
            samples: completed,
            audioWorkletOutputAtMs: Date.now(),
            callbackCount: this.callbackCount,
            postMessageCount: this.postMessageCount,
            allocationCount: this.allocationCount,
          }, [completed.buffer]);
        }
      }
    }
    return true;
  }
}

registerProcessor("offersteady-pcm-capture", OfferSteadyPcmCaptureProcessor);
