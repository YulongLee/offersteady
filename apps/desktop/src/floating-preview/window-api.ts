export interface FloatingWindowState {
  readonly productionBuild: boolean;
  readonly transparency: number;
  readonly protection: "requested" | "unavailable" | "unsupported";
  readonly status: "loading" | "ready" | "failed";
  readonly host: string;
  readonly canTuckAway: boolean;
}

declare global {
  interface Window {
    readonly floatingPreview: {
      state(): Promise<FloatingWindowState>;
      setTransparency(percentage: number): Promise<FloatingWindowState>;
      retry(): Promise<void>;
      tuckAway(): Promise<void>;
      onStatus(listener: (state: FloatingWindowState) => void): () => void;
    };
  }
}
