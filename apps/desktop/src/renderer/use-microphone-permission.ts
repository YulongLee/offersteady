import { useEffect, useRef } from "react";
import { MicrophonePermissionController, type MicrophonePermissionState } from "./microphone-permission";

/** Keep permission recovery independent of registration without adding any UI. */
export function useMicrophonePermission(enabled: boolean, onPermission: (state: MicrophonePermissionState) => void) {
  const controller = useRef<MicrophonePermissionController | null>(null);
  const callback = useRef(onPermission);
  callback.current = onPermission;

  useEffect(() => {
    if (!enabled) return;
    const current = new MicrophonePermissionController({
      read: async () => (await window.offersteady.getNativeRuntimeHealth?.())?.microphonePermission,
      request: () => window.offersteady.requestMicrophoneAccess(),
      openSettings: () => window.offersteady.openPermissionSettings("microphone"),
    }, next => callback.current(next));
    controller.current = current;
    void current.refresh(true);
    const refresh = () => { void current.refresh(); };
    const visible = () => { if (document.visibilityState === "visible") refresh(); };
    window.addEventListener("focus", refresh);
    document.addEventListener("visibilitychange", visible);
    return () => {
      current.dispose();
      controller.current = null;
      window.removeEventListener("focus", refresh);
      document.removeEventListener("visibilitychange", visible);
    };
  }, [enabled]);

  return { refresh: () => controller.current?.refresh(true) };
}
