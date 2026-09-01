import { readRuntimeConfig } from "./runtime-config";

const marker = "offersteady_pq=1";
const qualificationKey = "offersteady.promotion.qualification_event";

const eventId = () => {
  const existing = window.sessionStorage?.getItem(qualificationKey);
  if (existing) return existing;
  const next = typeof crypto?.randomUUID === "function" ? crypto.randomUUID() : `visit-${Date.now()}-${Math.random().toString(36).slice(2)}`;
  window.sessionStorage?.setItem(qualificationKey, next);
  return next;
};

export const installPromotionQualification = () => {
  if (typeof document === "undefined" || !document.cookie.split("; ").includes(marker)) return () => undefined;
  const startedAt = performance.now();
  let timer: number | undefined;
  const send = () => {
    if (document.visibilityState !== "visible") return;
    const visibleMs = Math.max(0, Math.round(performance.now() - startedAt));
    const config = readRuntimeConfig(import.meta.env);
    const base = config.apiBaseUrl.replace(/\/$/, "").replace(/\/api\/v1$/, "");
    void fetch(`${base}/api/v1/promotion/qualify`, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ eventId: eventId(), visibleMs, pageVisible: true }),
      keepalive: true,
    }).catch(() => undefined);
    document.cookie = "offersteady_pq=; Max-Age=0; Path=/; SameSite=Lax";
    document.removeEventListener("visibilitychange", visibleHandler);
  };
  const visibleHandler = () => {
    if (document.visibilityState === "visible" && timer === undefined) timer = window.setTimeout(send, 850);
  };
  visibleHandler();
  document.addEventListener("visibilitychange", visibleHandler);
  return () => {
    if (timer !== undefined) window.clearTimeout(timer);
    document.removeEventListener("visibilitychange", visibleHandler);
  };
};
