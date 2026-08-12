const DEFAULT_VERSION_CHECK_INTERVAL_MS = 5 * 60 * 1000;
const RELOAD_GUARD_KEY = "offersteady:web-version-reload";

export type WebVersionCheckRuntime = {
  fetchHtml: () => Promise<string>;
  currentEntryUrl: () => string | null;
  reload: () => void;
  getReloadGuard: () => string | null;
  setReloadGuard: (value: string) => void;
};

function normalizeEntryUrl(value: string, origin = window.location.origin): string {
  const url = new URL(value, origin);
  return `${url.pathname}${url.search}`;
}

export function extractModuleEntryUrl(html: string): string | null {
  const document = new DOMParser().parseFromString(html, "text/html");
  return document.querySelector<HTMLScriptElement>('script[type="module"][src]')?.getAttribute("src") ?? null;
}

export async function checkForWebVersionUpdate(runtime: WebVersionCheckRuntime): Promise<boolean> {
  const currentEntry = runtime.currentEntryUrl();
  if (!currentEntry) {
    return false;
  }

  const latestEntry = extractModuleEntryUrl(await runtime.fetchHtml());
  if (!latestEntry || normalizeEntryUrl(latestEntry) === normalizeEntryUrl(currentEntry)) {
    return false;
  }

  const reloadTarget = normalizeEntryUrl(latestEntry);
  if (runtime.getReloadGuard() === reloadTarget) {
    return false;
  }

  runtime.setReloadGuard(reloadTarget);
  runtime.reload();
  return true;
}

function createBrowserRuntime(): WebVersionCheckRuntime {
  return {
    fetchHtml: async () => {
      const response = await fetch(`/?__web_version=${Date.now()}`, {
        cache: "no-store",
        credentials: "same-origin",
        headers: { Accept: "text/html" },
      });
      if (!response.ok) {
        throw new Error(`Web version check failed with ${response.status}`);
      }
      return response.text();
    },
    currentEntryUrl: () =>
      document.querySelector<HTMLScriptElement>('script[type="module"][src]')?.getAttribute("src") ?? null,
    reload: () => window.location.reload(),
    getReloadGuard: () => sessionStorage.getItem(RELOAD_GUARD_KEY),
    setReloadGuard: (value) => sessionStorage.setItem(RELOAD_GUARD_KEY, value),
  };
}

export function installWebVersionRefresh(intervalMs = DEFAULT_VERSION_CHECK_INTERVAL_MS): () => void {
  const runtime = createBrowserRuntime();
  const check = () => {
    void checkForWebVersionUpdate(runtime).catch(() => {
      // A version probe must never replace the application's own backend recovery UI.
    });
  };
  const onVisibilityChange = () => {
    if (document.visibilityState === "visible") {
      check();
    }
  };

  window.addEventListener("online", check);
  document.addEventListener("visibilitychange", onVisibilityChange);
  const intervalId = window.setInterval(check, intervalMs);

  return () => {
    window.removeEventListener("online", check);
    document.removeEventListener("visibilitychange", onVisibilityChange);
    window.clearInterval(intervalId);
  };
}
