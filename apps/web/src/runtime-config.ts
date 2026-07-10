import type { PublicRuntimeEnv } from "@offersteady/config";
import { readPublicRuntimeConfig } from "@offersteady/config";

export interface RuntimeConfig {
  readonly appEnv: "development" | "test" | "staging" | "production";
  readonly apiBaseUrl: string;
  readonly appVersion: string;
}

export type RuntimeEnv = PublicRuntimeEnv;

export const readRuntimeConfig = (env: RuntimeEnv): RuntimeConfig => readPublicRuntimeConfig(env);
