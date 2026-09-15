import { lazy } from "react";

let livePagePromise: Promise<typeof import("./LivePage")> | undefined;

export function loadLivePage() {
  // A failed optional warm-up must not poison the later navigation attempt.
  livePagePromise ??= import("./LivePage").catch(error => {
    livePagePromise = undefined;
    throw error;
  });
  return livePagePromise;
}

export const LivePage = lazy(() => loadLivePage().then(module => ({ default: module.LivePage })));

export async function preloadLivePage(): Promise<void> {
  // Preparation only warms modules: no capture, session or answer is started.
  await Promise.allSettled([loadLivePage(), import("./AnswerWorkspace")]);
}
