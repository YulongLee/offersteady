/// <reference types="vite/client" />

declare module "*.txt?raw" {
  const content: string;
  export default content;
}

interface ImportMetaEnv {
  readonly VITE_GLOBAL_LOCALE?: "en-US" | "en-GB" | "en-AU" | "en-CA";
  readonly VITE_GLOBAL_COMMERCE_ENABLED?: "true" | "false";
  readonly VITE_GLOBAL_COMMERCE_PROVIDER?: "none" | "creem";
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
