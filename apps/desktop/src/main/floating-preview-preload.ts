import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("floatingPreview", {
  state: () => ipcRenderer.invoke("floating-preview:state"),
  setTransparency: (percentage: number) => ipcRenderer.invoke("floating-preview:transparency", percentage),
  retry: () => ipcRenderer.invoke("floating-preview:retry"),
  tuckAway: () => ipcRenderer.invoke("floating-preview:tuck-away"),
  onStatus: (listener: (state: unknown) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, state: unknown) => listener(state);
    ipcRenderer.on("floating-preview:status", handler);
    return () => ipcRenderer.removeListener("floating-preview:status", handler);
  },
});
