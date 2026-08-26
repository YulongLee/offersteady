export type ScreenPermissionStatus = "not-determined" | "granted" | "denied" | "restricted" | "unknown";

export const canAcquireDisplaySources = (platform: NodeJS.Platform, status: ScreenPermissionStatus) =>
  platform !== "darwin" || status === "granted";

export type DisplayMediaResolution<T> =
  | { readonly kind: "ready"; readonly source: T }
  | { readonly kind: "permission-required" }
  | { readonly kind: "unavailable"; readonly error: unknown };

export const resolveDisplayMediaSource = async <T>(input: {
  readonly platform: NodeJS.Platform;
  readonly permissionStatus: ScreenPermissionStatus;
  readonly getSources: () => Promise<readonly T[]>;
  readonly preferredSourceId?: string | null;
  readonly sourceId: (source: T) => string;
}): Promise<DisplayMediaResolution<T>> => {
  if (!canAcquireDisplaySources(input.platform, input.permissionStatus)) {
    return { kind: "permission-required" };
  }
  try {
    const sources = await input.getSources();
    const source = (input.preferredSourceId
      ? sources.find((candidate) => input.sourceId(candidate) === input.preferredSourceId)
      : undefined) ?? sources[0];
    return source ? { kind: "ready", source } : { kind: "unavailable", error: new Error("display-source-unavailable") };
  } catch (error) {
    return { kind: "unavailable", error };
  }
};
