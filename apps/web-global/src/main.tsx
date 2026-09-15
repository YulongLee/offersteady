import "./legacy-browser-polyfills";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { applyStoredAppearancePreferences } from "./appearance-preferences";
import { installWebVersionRefresh } from "./web-version-refresh";
import { installPromotionQualification } from "./promotion-attribution";
import { clearAppEntryShell } from "./app-entry-shell";

applyStoredAppearancePreferences();
installWebVersionRefresh();
installPromotionQualification();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

// Keep the pre-mount shell in place until React has committed the first frame.
window.requestAnimationFrame(clearAppEntryShell);
