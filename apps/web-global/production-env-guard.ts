export interface ProductionWebBuildEnvironment {
  readonly VITE_APP_ENV?: string;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_PUBLIC_APP_VERSION?: string;
}

const LOOPBACK_HOSTS = new Set(["localhost", "127.0.0.1", "0.0.0.0", "::1"]);

export const validateProductionWebBuildEnvironment = (
  mode: string,
  env: ProductionWebBuildEnvironment,
): void => {
  if (mode !== "production") return;
  if (env.VITE_APP_ENV !== "production") {
    throw new Error("Production Web build requires VITE_APP_ENV=production.");
  }
  const rawApiBaseUrl = env.VITE_API_BASE_URL?.trim();
  if (!rawApiBaseUrl) {
    throw new Error("Production Web build requires an explicit VITE_API_BASE_URL (use / for same-origin API requests).");
  }
  if (rawApiBaseUrl !== "/") {
    let parsed: URL;
    try {
      parsed = new URL(rawApiBaseUrl);
    } catch {
      throw new Error("Production VITE_API_BASE_URL must be / or an absolute HTTPS URL.");
    }
    if (parsed.protocol !== "https:") {
      throw new Error("Production VITE_API_BASE_URL must use HTTPS.");
    }
    if (LOOPBACK_HOSTS.has(parsed.hostname.toLowerCase())) {
      throw new Error("Production VITE_API_BASE_URL must not point to a loopback host.");
    }
  }
  if (!env.VITE_PUBLIC_APP_VERSION?.trim()) {
    throw new Error("Production Web build requires VITE_PUBLIC_APP_VERSION.");
  }
};
