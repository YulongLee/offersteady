import React from "react";
import {
  Audio,
  Sequence,
  staticFile,
  interpolate,
  useCurrentFrame,
} from "remotion";
import measurements from "../reference/sfx-measurements.json";
export const OUTPUT_AUDIO_OFFSET_F = 2.56;
// Final mastering gain: +7 dB, verified true peak remains below -3 dBTP.
const MASTER_GAIN = Math.pow(10, 7 / 20);
const peak = (src: keyof typeof measurements) => measurements[src].peakFrame;
export const soundFrom = (target: number, src: keyof typeof measurements) =>
  Math.max(0, Math.round(target - peak(src) - OUTPUT_AUDIO_OFFSET_F));
export const AudioProbe = () => (
  <>
    <Sequence from={30} durationInFrames={30}>
      <Audio src={staticFile("audio/click-camera.mp3")} />
    </Sequence>
    <Sequence from={120} durationInFrames={120}>
      <Audio src={staticFile("audio/impact-deep-whoosh.mp3")} volume={0.3} />
    </Sequence>
  </>
);
export const Soundtrack: React.FC<{ bgm: boolean; sfx: boolean }> = ({
  bgm,
  sfx,
}) => {
  const f = useCurrentFrame();
  const SH = {
    open: 0,
    context: 240,
    listen: 540,
    answer: 900,
    screen: 1320,
    outro: 1740,
  };
  const sounds: [number, keyof typeof measurements, number, number, string][] =
    [
      [SH.open + 55, "transition-soft.mp3", 0.15, 78, "control establishes"],
      [SH.open + 165, "whoosh-fast.mp3", 0.2, 106, "camera pulls back"],
      [SH.context + 72, "transition-soft.mp3", 0.16, 78, "materials arrive"],
      [SH.context + 140, "whoosh-fast.mp3", 0.12, 106, "materials settle"],
      [
        SH.listen + 288,
        "click-camera.mp3",
        0.5,
        22,
        "explicit quick-answer click",
      ],
      [SH.answer + 60, "transition-soft.mp3", 0.15, 78, "summary is readable"],
      [
        SH.answer + 370,
        "whoosh-fast.mp3",
        0.14,
        106,
        "answer closeup exits",
      ],
      [
        SH.screen + 140,
        "click-camera.mp3",
        0.52,
        22,
        "explicit screenshot click",
      ],
      [
        SH.screen + 215,
        "transition-soft.mp3",
        0.2,
        78,
        "screenshot response emerges",
      ],
      [SH.outro + 165, "riser-rise.mp3", 0.12, 210, "brand build"],
      [SH.outro + 210, "impact-deep-whoosh.mp3", 0.23, 210, "brand lands"],
      [SH.outro + 286, "shimmer-sparkle-sweep.mp3", 0.17, 180, "brand afterglow"],
    ];
  return (
    <>
      {bgm ? (
        <Audio
          src={staticFile("audio/bgm-source.mp3")}
          volume={MASTER_GAIN * interpolate(f, [0, 90, 1950, 2159], [0, 0.19, 0.19, 0], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          })}
        />
      ) : null}
      {sfx
        ? sounds.map(([target, src, volume, duration, label]) => (
            <Sequence
              key={label}
              from={soundFrom(target, src)}
              durationInFrames={Math.min(
                duration,
                2160 - soundFrom(target, src),
              )}
            >
              <Audio
                src={staticFile(`audio/${src}`)}
                volume={(af) =>
                  MASTER_GAIN * volume *
                  interpolate(
                    af,
                    [0, 4, duration - 12, duration],
                    [0, 1, 1, 0],
                    { extrapolateLeft: "clamp", extrapolateRight: "clamp" },
                  )
                }
              />
            </Sequence>
          ))
        : null}
    </>
  );
};
