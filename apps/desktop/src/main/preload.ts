import { contextBridge, ipcRenderer } from "electron";
import type { CaptureState } from "@offersteady/protocol" with { "resolution-mode": "import" };

contextBridge.exposeInMainWorld("offersteady", {
  publishCaptureState: (state: CaptureState) => ipcRenderer.send("capture:set-state", state),
  saveDeviceCredential: (credential: string) => ipcRenderer.invoke("credential:save", credential),
  clearDeviceCredential: () => ipcRenderer.invoke("credential:clear"),
  getDesktopConfig: () => ipcRenderer.invoke("desktop:get-config"),
  getNativeRuntimeHealth: () => ipcRenderer.invoke("desktop:get-native-runtime-health"),
  startNativeAudioStream: (options: {
    microphoneSourceId?: string;
    systemSourceId?: string;
    captureMicrophone?: boolean;
    captureSystem?: boolean;
  }) => ipcRenderer.invoke("desktop:start-native-audio-stream", options),
  stopNativeAudioStream: () => ipcRenderer.invoke("desktop:stop-native-audio-stream"),
  onNativeAudioEvent: (callback: (event: unknown) => void) => {
    const listener = (_event: Electron.IpcRendererEvent, payload: unknown) => callback(payload);
    ipcRenderer.on("desktop:native-audio-event", listener);
    return () => ipcRenderer.removeListener("desktop:native-audio-event", listener);
  },
  getPairingIdentity: () => ipcRenderer.invoke("desktop:get-pairing-identity"),
  resetPairingIdentity: () => ipcRenderer.invoke("desktop:reset-pairing-identity"),
  listScreens: () => ipcRenderer.invoke("desktop:list-screens"),
  setPreferredScreen: (screenSourceId: string | null) => ipcRenderer.invoke("desktop:set-preferred-screen", screenSourceId),
  captureCurrentScreen: (screenSourceId?: string | null) => ipcRenderer.invoke("desktop:capture-current-screen", screenSourceId ?? null),
  uploadScreenshotCapture: (request: {
    url: string;
    deviceId: string;
    manualCode: string;
    dataUrl: string;
    filename: string;
  }) => ipcRenderer.invoke("desktop:upload-screenshot-capture", request),
  openExternal: (url: string) => ipcRenderer.invoke("desktop:open-external", url),
  probeWebUrl: (url: string) => ipcRenderer.invoke("desktop:probe-web-url", url),
  apiRequest: (request: { url: string; method?: string; headers?: Record<string, string>; body?: string | null }) => ipcRenderer.invoke("desktop:api-request", request),
  requestMicrophoneAccess: () => ipcRenderer.invoke("desktop:request-microphone-access"),
  openPermissionSettings: (kind: "microphone" | "screen" | "camera" | "audio") => ipcRenderer.invoke("desktop:open-permission-settings", kind),
  requestClose: () => ipcRenderer.send("app:close"),
});
