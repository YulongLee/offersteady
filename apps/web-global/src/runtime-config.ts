import type { PublicRuntimeEnv } from "@offersteady/config";
import { readPublicRuntimeConfig } from "@offersteady/config";

export interface RuntimeConfig {
  readonly appEnv: "development" | "test" | "staging" | "production";
  readonly apiBaseUrl: string;
  readonly appVersion: string;
  readonly productEdition: "global";
  readonly locale: GlobalLocale;
  readonly commerceProvider: "none" | "creem";
  readonly commerceEnabled: boolean;
}

export const globalLocales = ["en-US", "en-GB", "en-AU", "en-CA"] as const;
export type GlobalLocale = (typeof globalLocales)[number];

export type RuntimeEnv = PublicRuntimeEnv & {
  readonly VITE_GLOBAL_LOCALE?: string;
  readonly VITE_GLOBAL_COMMERCE_PROVIDER?: string;
  readonly VITE_GLOBAL_COMMERCE_ENABLED?: string;
};

export const parseGlobalLocale = (value: string | undefined): GlobalLocale =>
  globalLocales.includes(value as GlobalLocale) ? value as GlobalLocale : "en-US";

export const readRuntimeConfig = (env: RuntimeEnv): RuntimeConfig => ({
  ...readPublicRuntimeConfig(env),
  productEdition: "global",
  locale: parseGlobalLocale(env.VITE_GLOBAL_LOCALE),
  commerceProvider: env.VITE_GLOBAL_COMMERCE_PROVIDER === "creem" ? "creem" : "none",
  commerceEnabled: env.VITE_GLOBAL_COMMERCE_ENABLED === "true" && env.VITE_GLOBAL_COMMERCE_PROVIDER === "creem",
});
