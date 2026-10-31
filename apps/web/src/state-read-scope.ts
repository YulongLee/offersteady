// This is a freshness barrier, not a cache. No response or credential is stored.
let generation = 0;

export const stateReadGeneration = () => generation;
export const invalidateStateReads = () => { generation += 1; };

export const isStateAffectingRequest = (path: string, method = "GET") => {
  const pathname = new URL(path, "https://state-scope.invalid").pathname;
  const verb = method.toUpperCase();
  // Order lookup can reconcile a provider payment; a fresh billing read also
  // must not be overwritten by an older full-state response.
  if (verb === "GET" && /^\/api\/v1\/billing\/(?:state|checkout-orders\/[^/]+)$/.test(pathname)) return true;
  if (["GET", "HEAD", "OPTIONS"].includes(verb)) return false;
  if (/\/(?:performance-ack|delivery-metrics|performance-summary|web-heartbeat|heartbeat|device-status|snapshot)(?:\/|$)/.test(pathname)) return false;
  if (/\/(?:quote|quotes|preview|estimate|search)(?:\/|$)/.test(pathname)) return false;
  if (/^\/api\/v1\/(?:sessions|documents|document-processing|resume|job-descriptions|knowledge|billing|mock-interviews|resume-optimizer|live-answer|chat|screenshot-answer|partner-program)(?:\/|$)/.test(pathname)) return true;
  return /^\/api\/v1\/realtime-speech\//.test(pathname)
    && /\/(?:connect|disconnect|capture-control|desktop-binding)(?:\/|$)/.test(pathname);
};

export const beginStateMutation = (path: string, method = "GET"): (() => void) => {
  if (!isStateAffectingRequest(path, method)) return () => undefined;
  invalidateStateReads();
  let finished = false;
  return () => {
    if (finished) return;
    finished = true;
    // A failed transport may have committed on the server, so always invalidate.
    invalidateStateReads();
  };
};

export const stateReadCancelled = () => new DOMException("页面状态已更新，请重试。", "AbortError");
export const isStateReadCancelled = (error: unknown) => error instanceof DOMException && error.name === "AbortError";
