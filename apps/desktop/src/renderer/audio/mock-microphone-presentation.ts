import type { AudioSourceHealth } from "@offersteady/protocol";
import { sourceSignalVerificationThreshold } from "./audio-readiness";

export type MockMicrophoneState = "capturing" | "paused" | "error" | null;

export const mockMicrophoneHealth = (
  state: MockMicrophoneState, level: number | null, sourceId: string,
): AudioSourceHealth => ({
  sourceId, sourceKind: "microphone", label: "麦克风",
  state: state === "error" ? "error" : state === "capturing" && level !== null
    ? level >= sourceSignalVerificationThreshold("microphone") ? "receiving" : "silent" : "unknown",
  ...(state === "error" ? { stage: "failed" as const } : state === "capturing" ? { stage: "stream-opened" as const } : {}),
  level: state === "capturing" ? level ?? 0 : 0,
});

export const mockMicrophoneMeterCopy = (state: MockMicrophoneState, level: number | null): string => {
  if (state === "error") return "麦克风启动失败";
  if (state === "paused") return "提问或暂停中，麦克风不会上传";
  if (state === "capturing" && level !== null && level >= sourceSignalVerificationThreshold("microphone")) return "正在采集你的回答";
  if (state === "capturing") return "麦克风已就绪，等待声音";
  return "等待模拟面试收音";
};
