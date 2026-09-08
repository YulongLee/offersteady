export type DesktopProductEdition = "domestic" | "global";

export const resolveDesktopProductEdition = (input: {
  readonly explicitEdition?: string;
  readonly hasPackagedGlobalRuntimeConfig: boolean;
  readonly applicationName?: string;
}): DesktopProductEdition => {
  if (input.explicitEdition === "global") return "global";
  if (input.hasPackagedGlobalRuntimeConfig) return "global";
  return /\bglobal\b/i.test(input.applicationName ?? "") ? "global" : "domestic";
};
