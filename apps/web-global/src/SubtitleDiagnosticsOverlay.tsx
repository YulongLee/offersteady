import { useEffect, useState } from "react";
import {
  getSubtitleDiagnosticsSnapshot,
  subscribeSubtitleDiagnostics,
  subtitleRevisionDiagnosticsEnabled,
  type SubtitleRevisionStage,
} from "./realtime-subtitle-diagnostics";

const stageLabels: readonly [SubtitleRevisionStage, string][] = [
  ["qwen", "Qwen Partial"],
  ["sse-yield", "SSE Yield"],
  ["browser-parse", "Browser Parse"],
  ["store-complete", "State Update"],
  ["react-commit", "React Commit"],
  ["paint", "Paint"],
];

export function SubtitleDiagnosticsOverlay() {
  const [snapshot, setSnapshot] = useState(getSubtitleDiagnosticsSnapshot);
  const [, setClock] = useState(0);
  useEffect(() => subscribeSubtitleDiagnostics(() => setSnapshot(getSubtitleDiagnosticsSnapshot())), []);
  useEffect(() => {
    if (!subtitleRevisionDiagnosticsEnabled()) return;
    const timer = window.setInterval(() => setClock(current => current + 1), 250);
    return () => window.clearInterval(timer);
  }, []);
  if (!subtitleRevisionDiagnosticsEnabled()) return null;
  const now = Date.now();
  return <aside className="subtitle-diagnostics-overlay" aria-label="实时字幕诊断">
    <strong>SUBTITLE TRACE</strong>
    <span>Revision: {snapshot.currentRevision || "-"}</span>
    {stageLabels.map(([stage, label]) => <span key={stage}>
      {label}: {snapshot.stageCounts[stage]} · age {snapshot.latestStageAtMs[stage] === undefined ? "-" : `${Math.max(0, now - snapshot.latestStageAtMs[stage]!)}ms`}
    </span>)}
    <span>Remote Qwen / SSE: {snapshot.remoteStageCounts.qwen ?? "-"} / {snapshot.remoteStageCounts.sse ?? "-"}</span>
    <span>visibility: {snapshot.visibilityState}</span>
  </aside>;
}
