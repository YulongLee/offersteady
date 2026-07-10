export const publicRuntimeEnvKeys = {
  appEnv: "VITE_APP_ENV",
  apiBaseUrl: "VITE_API_BASE_URL",
  publicAppVersion: "VITE_PUBLIC_APP_VERSION",
} as const;

export interface PublicRuntimeEnv {
  readonly VITE_APP_ENV?: string;
  readonly VITE_API_BASE_URL?: string;
  readonly VITE_PUBLIC_APP_VERSION?: string;
}

export interface PublicRuntimeConfig {
  readonly appEnv: "development" | "test" | "staging" | "production";
  readonly apiBaseUrl: string;
  readonly appVersion: string;
}

export const normalizePublicAppEnv = (value: string | undefined): PublicRuntimeConfig["appEnv"] => {
  if (value === "test" || value === "staging" || value === "production") return value;
  return "development";
};

export const normalizeApiBaseUrl = (value: string | undefined, fallback = "http://127.0.0.1:8000") =>
  (value ?? fallback).replace(/\/+$/, "").replace(/\/api\/v1$/, "");

export const readPublicRuntimeConfig = (env: PublicRuntimeEnv): PublicRuntimeConfig => ({
  appEnv: normalizePublicAppEnv(env.VITE_APP_ENV),
  apiBaseUrl: normalizeApiBaseUrl(env.VITE_API_BASE_URL),
  appVersion: env.VITE_PUBLIC_APP_VERSION?.trim() || "0.1.0",
});

export const structuredLogFields = [
  "timestamp",
  "level",
  "service",
  "environment",
  "request_id",
  "feature",
  "action",
  "error_code",
] as const;
