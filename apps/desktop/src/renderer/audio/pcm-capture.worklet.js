class OfferSteadyPcmCaptureProcessor extends AudioWorkletProcessor {
  process(inputs, outputs) {
    const input = inputs[0]?.[0];
    const output = outputs[0]?.[0];
    if (output) output.fill(0);
    if (input && input.length > 0) {
      const copy = new Float32Array(input);
      this.port.postMessage(copy, [copy.buffer]);
    }
    return true;
  }
}

registerProcessor("offersteady-pcm-capture", OfferSteadyPcmCaptureProcessor);
