import { useEffect, useRef, useState } from "react";
import { MicrophonePermissionController, microphonePermissionCopy, type MicrophonePermissionState } from "./microphone-permission";

export function MicrophonePermissionPanel({ onPermission }: { readonly onPermission: (state: MicrophonePermissionState) => void }) {
  const [state, setState] = useState<MicrophonePermissionState>("checking");
  const controller = useRef<MicrophonePermissionController | null>(null);
  const callback = useRef(onPermission);
  callback.current = onPermission;

  useEffect(() => {
    const current = new MicrophonePermissionController({
      read: async () => (await window.offersteady.getNativeRuntimeHealth?.())?.microphonePermission,
      request: () => window.offersteady.requestMicrophoneAccess(),
      openSettings: () => window.offersteady.openPermissionSettings("microphone"),
    }, next => { setState(next); callback.current(next); });
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
  }, []);

  return <section className="microphone-permission-panel" aria-label="麦克风授权" data-state={state}>
    <p role="status">{microphonePermissionCopy[state]}</p>
    <div className="microphone-permission-actions">
      {(state === "not-determined" || state === "error") && <button type="button" className="secondary-button" onClick={() => { void controller.current?.request(); }}>申请麦克风授权</button>}
      <button type="button" className="secondary-button" onClick={() => { void controller.current?.refresh(); }}>检查权限</button>
      <button type="button" className="secondary-button" onClick={() => { void controller.current?.openSettings(); }}>打开系统设置</button>
    </div>
  </section>;
}
