import type { WebAppState } from "./domain";

const terminalStatuses = new Set(["ready", "failed", "deleted", "disabled"]);

type LoadState = (signal: AbortSignal) => Promise<WebAppState>;
type Sleep = (delayMs: number, signal: AbortSignal) => Promise<void>;

export type LibraryProcessingPollResult =
  | { readonly kind: "settled"; readonly state: WebAppState }
  | { readonly kind: "timeout" };

const defaultSleep: Sleep = (delayMs, signal) =>
  new Promise<void>((resolve, reject) => {
    const timer = window.setTimeout(() => {
      signal.removeEventListener("abort", abort);
      resolve();
    }, delayMs);
    const abort = () => {
      window.clearTimeout(timer);
      signal.removeEventListener("abort", abort);
      reject(new DOMException("The operation was aborted", "AbortError"));
    };
    if (signal.aborted) {
      abort();
      return;
    }
    signal.addEventListener("abort", abort, { once: true });
  });

export async function pollLibraryDocumentUntilSettled({
  documentId,
  loadState,
  signal,
  maxAttempts = 45,
  sleep = defaultSleep,
}: {
  readonly documentId: string;
  readonly loadState: LoadState;
  readonly signal: AbortSignal;
  readonly maxAttempts?: number;
  readonly sleep?: Sleep;
}): Promise<LibraryProcessingPollResult> {
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    await sleep(attempt === 0 ? 800 : 2000, signal);
    const next = await loadState(signal);
    const source = next.librarySources.find((item) => item.id === documentId);
    const document = next.knowledgeDocuments.find(
      (item) => item.id === documentId,
    );
    const status = source?.status ?? document?.status;
    if (status && terminalStatuses.has(status)) {
      return { kind: "settled", state: next };
    }
  }
  return { kind: "timeout" };
}
