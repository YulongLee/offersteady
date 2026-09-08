import {readFile, writeFile} from "node:fs/promises";

const beatData = JSON.parse(await readFile("reference/beat-data.json", "utf8"));
const offsetData = JSON.parse(
  await readFile("reference/output-offset-probe.json", "utf8"),
);
const boundaries = [239, 543, 903, 1319, 1734];
const fps = 60;
const offsetFrames = offsetData.offsetFrames;

const checks = boundaries.map((boundaryFrame) => {
  const nearest = beatData.beats.reduce((best, seconds) => {
    const sourceFrame = seconds * fps;
    return Math.abs(sourceFrame - boundaryFrame) <
      Math.abs(best.sourceFrame - boundaryFrame)
      ? {seconds, sourceFrame}
      : best;
  }, {seconds: beatData.beats[0], sourceFrame: beatData.beats[0] * fps});
  const audibleFrame = nearest.sourceFrame + offsetFrames;
  return {
    boundaryFrame,
    beatSeconds: Number(nearest.seconds.toFixed(6)),
    sourceBeatFrame: Number(nearest.sourceFrame.toFixed(3)),
    audibleBeatFrame: Number(audibleFrame.toFixed(3)),
    sourceErrorFrames: Number(
      Math.abs(boundaryFrame - nearest.sourceFrame).toFixed(3),
    ),
    audibleErrorFrames: Number(
      Math.abs(boundaryFrame - audibleFrame).toFixed(3),
    ),
  };
});

const result = {
  bpm: beatData.bpm,
  fps,
  encodedAudioOffsetFrames: offsetFrames,
  toleranceFrames: 3,
  maxSourceErrorFrames: Math.max(...checks.map((item) => item.sourceErrorFrames)),
  maxAudibleErrorFrames: Math.max(...checks.map((item) => item.audibleErrorFrames)),
  pass: checks.every(
    (item) => item.sourceErrorFrames <= 3 && item.audibleErrorFrames <= 3,
  ),
  checks,
};

await writeFile(
  "out/qa/beat-boundaries.json",
  `${JSON.stringify(result, null, 2)}\n`,
);
console.log(JSON.stringify(result, null, 2));
