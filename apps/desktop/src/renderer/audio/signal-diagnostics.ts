export const calculateRms = (samples: ArrayLike<number>): number => {
  if (samples.length === 0) return 0;
  let sum = 0;
  for (let index = 0; index < samples.length; index += 1) {
    const sample = samples[index] ?? 0;
    sum += sample * sample;
  }
  return Math.sqrt(sum / samples.length);
};

export const isSilent = (samples: ArrayLike<number>, threshold = 0.008): boolean =>
  calculateRms(samples) < threshold;
