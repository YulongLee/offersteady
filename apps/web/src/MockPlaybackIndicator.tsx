import { useEffect, useState } from "react";
import { MOCK_WAVEFORM_BARS, type MockPlaybackFrame, type MockSession, type MockVoicePlayer } from "./mock-interview-client";

const silentFrame: MockPlaybackFrame = { playing: false, levels: Array<number>(MOCK_WAVEFORM_BARS).fill(0) };

/** Only this small view updates with playback; no microphone or billing commands. */
export function MockPlaybackIndicator({ player, phase }: { player: MockVoicePlayer; phase: MockSession["state"]["phase"] }) {
  const [frame, setFrame] = useState(silentFrame);
  const [reducedMotion, setReducedMotion] = useState(false);
  useEffect(() => {
    const preference = window.matchMedia?.("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(preference?.matches ?? false);
    update();
    preference?.addEventListener("change", update);
    return () => preference?.removeEventListener("change", update);
  }, []);
  useEffect(() => player.subscribePlayback(next => {
    if (!reducedMotion) setFrame(next);
    else setFrame(previous => previous.playing === next.playing ? previous : { ...silentFrame, playing: next.playing });
  }), [player, reducedMotion]);

  const active = phase === "speaking" && frame.playing;
  const label = active ? "面试官正在提问" : phase === "speaking" ? "等待语音播放"
    : phase === "paused" ? "语音播放已暂停" : phase === "listening" ? "正在聆听你的回答" : "等待面试官提问";
  return <div className={`mock-playback ${active ? "is-active" : ""} ${reducedMotion ? "is-reduced-motion" : ""}`}>
    <div className="mock-waveform" aria-hidden="true">
      {frame.levels.map((level, index) => <span key={index} style={{ transform: `scaleY(${active && !reducedMotion ? 0.12 + level * 0.88 : 0.12})` }} />)}
    </div>
    <span className="mock-playback-label" role="status"><i aria-hidden="true" />{label}</span>
  </div>;
}
