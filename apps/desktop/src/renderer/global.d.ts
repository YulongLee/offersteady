import type { CaptureState, DesktopArchitecture, DesktopPlatform } from "@offersteady/protocol";

export interface DesktopRuntimeConfig {
  readonly appVersion: string;
  readonly platform: DesktopPlatform;
  readonly architecture: DesktopArchitecture;
  readonly platformVersion: string;
  readonly protocolVersion: string;
  readonly captureRuntime: "electron-single-owner";
  readonly webWorkspaceUrl: string;
  readonly apiBaseUrl: string;
  readonly realtimeEndpointing: {
    readonly mode: "legacy-threshold" | "commercial-adaptive";
  };
}

export interface DesktopPairingIdentity {
  readonly deviceId: string;
  readonly manualCode: string;
  readonly displayName: string;
}

export interface DesktopScreenSource {
  readonly id: string;
  readonly label: string;
  readonly thumbnailDataUrl?: string | null;
}

export interface DesktopNativeRuntimeHealth {
  readonly available: boolean;
  readonly ready: boolean;
  readonly errorCode?: string;
  readonly message?: string;
  readonly runtime?: string;
  readonly version?: string;
  readonly microphonePermission?: string;
  readonly screenPermission?: string;
  readonly screenCaptureKitAvailable?: boolean;
  readonly computerOutputCapturePath?: string;
  readonly errors?: readonly string[];
}

export interface DesktopScreenshotShortcutSettings {
  readonly accelerator: string;
  readonly registered?: boolean;
  readonly message?: string;
  readonly options: readonly {
    readonly accelerator: string;
    readonly label: string;
  }[];
}

declare global {
  interface Window {
    offersteady: {
      publishCaptureState: (state: CaptureState) => void;
      publishScreenshotBinding?: (binding: { readonly sessionId: string; readonly bindingId: string } | null) => void;
      publishRendererReliabilityHeartbeat?: (heartbeat: Record<string, unknown>) => void;
      publishRealtimeTransportDiagnostics?: (snapshot: Record<string, unknown>) => void;
      getRendererRecoveryContext?: () => Promise<{
        readonly crashAtMs: number;
        readonly reason: string;
        readonly exitCode: number;
        readonly sessionId: string | null;
        readonly desiredCapture: boolean;
        readonly recoveryAttempt: number;
      } | null>;
      getRendererReliabilityDiagnostics?: () => Promise<Record<string, unknown>>;
      getRealtimeTransportDiagnosticsPath?: () => Promise<string | null>;
      completeRendererRecovery?: (input: { readonly sessionId: string; readonly ackAtMs: number }) => void;
      onRendererRecoveryRequested?: (listener: (context: Record<string, unknown>) => void) => () => void;
      saveDeviceCredential: (credential: string) => Promise<void>;
      clearDeviceCredential: () => Promise<void>;
      getDesktopConfig: () => Promise<DesktopRuntimeConfig>;
      getNativeRuntimeHealth?: () => Promise<DesktopNativeRuntimeHealth>;
      getScreenshotShortcut?: () => Promise<DesktopScreenshotShortcutSettings>;
      setScreenshotShortcut?: (accelerator: string) => Promise<{ ok: boolean; accelerator: string; message: string }>;
      getScreenshotCaptureLock?: () => Promise<{ locked: boolean; message: string }>;
      onScreenshotCaptureLockChanged?: (listener: (state: { locked: boolean; message: string }) => void) => () => void;
      onScreenshotShortcutNotice?: (listener: (message: string) => void) => () => void;
      getPairingIdentity: () => Promise<DesktopPairingIdentity>;
      listScreens?: () => Promise<readonly DesktopScreenSource[]>;
      setPreferredScreen?: (screenSourceId: string | null) => Promise<{ ok: boolean }>;
      captureCurrentScreen?: (screenSourceId?: string | null) => Promise<{
        readonly name?: string;
        readonly width?: number;
        readonly height?: number;
        readonly originalWidth?: number;
        readonly originalHeight?: number;
        readonly byteLength?: number;
        readonly contentType?: string;
        readonly extension?: string;
        readonly dataUrl?: string;
        readonly errorMessage?: string;
      }>;
      uploadScreenshotCapture?: (request: {
        readonly url: string;
        readonly deviceId: string;
        readonly manualCode: string;
        readonly dataUrl: string;
        readonly filename: string;
      }) => Promise<{
        readonly ok: boolean;
        readonly status: number;
        readonly statusText: string;
        readonly headers: Record<string, string>;
        readonly bodyText: string;
      }>;
      openExternal: (url: string) => Promise<void>;
      probeWebUrl: (url: string) => Promise<boolean>;
      apiRequest?: (request: {
        readonly url: string;
        readonly method?: string;
        readonly headers?: Record<string, string>;
        readonly body?: string | null;
      }) => Promise<{
        readonly ok: boolean;
        readonly status: number;
        readonly statusText: string;
        readonly headers: Record<string, string>;
        readonly bodyText: string;
      }>;
      requestMicrophoneAccess: () => Promise<boolean>;
      requestScreenCaptureAccess?: () => Promise<boolean>;
      resetPairingIdentity: () => Promise<boolean>;
      openPermissionSettings: (kind: "microphone" | "screen" | "camera" | "audio") => Promise<void>;
      requestClose: () => void;
    };
  }
}

export {};
