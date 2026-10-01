import { useEffect, useRef, useState } from "react";
import { authClient } from "./auth-client";
import { createJsonClient } from "./api-client";
import { readRuntimeConfig } from "./runtime-config";
import "./web-answer.css";

/** Per-session, opt-in only. No background polling or persisted enabled state. */
export function useWebAnswerControl(sessionId: string, written: boolean) {
  const [enabled, setEnabled] = useState(false);
  const enabledRef = useRef(false);
  const [access, setAccess] = useState<"loading" | "ready" | "membership" | "unavailable">("loading");
  useEffect(() => {
    enabledRef.current = false; setEnabled(false); setAccess("loading");
    if (written) { setAccess("unavailable"); return; }
    const controller = new AbortController();
    const auth = authClient.readStoredSession();
    if (!auth) { setAccess("membership"); return; }
    const client = createJsonClient({ baseUrl: readRuntimeConfig(import.meta.env).apiBaseUrl });
    const headers = { Authorization: `Bearer ${auth.accessToken}` };
    void Promise.all([
      client.request<{ webSearchEnabled: boolean; webSearchAvailable: boolean }>("/api/v1/live-answer/status", { headers }, controller.signal),
      client.request<{ features: { webAnswer?: boolean } }>("/api/v1/global-commerce/state", { headers }, controller.signal),
    ]).then(([status, member]) => {
      if (!controller.signal.aborted) setAccess(!status.webSearchEnabled || !status.webSearchAvailable ? "unavailable" : member.features.webAnswer ? "ready" : "membership");
    }).catch(() => { if (!controller.signal.aborted) setAccess("unavailable"); });
    return () => { controller.abort(); enabledRef.current = false; };
  }, [sessionId, written]);
  const change = (next: boolean) => {
    if (next && access !== "ready") return;
    enabledRef.current = next;
    setEnabled(next);
  };
  return { enabled, enabledRef, access, change };
}

export function WebAnswerToggle({ enabled, access, disabled, onChange }: {
  enabled: boolean; access: "loading" | "ready" | "membership" | "unavailable";
  disabled?: boolean; onChange: (next: boolean) => void;
}) {
  const hint = access === "loading" ? "Checking web answer availability"
    : access === "membership" ? "Requires an active membership purchased for 7 days or longer"
    : access === "unavailable" ? "Web answers are not available in this environment"
    : "Uses public web sources for detailed answers only. Quick answers do not use web search. Included with your membership.";
  return <button type="button" className={`web-answer-toggle ${enabled ? "is-on" : ""}`}
    role="switch" aria-checked={enabled} aria-label="Web answers" title={hint}
    disabled={disabled || (!enabled && access !== "ready")} onClick={() => onChange(!enabled)}>
    <span aria-hidden="true">◎</span> Web answers <span>{enabled ? "On" : "Off"}</span>
  </button>;
}
