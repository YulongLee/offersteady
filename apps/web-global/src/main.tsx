import "./legacy-browser-polyfills";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { applyStoredAppearancePreferences } from "./appearance-preferences";
import { installWebVersionRefresh } from "./web-version-refresh";
import { installPromotionQualification } from "./promotion-attribution";

applyStoredAppearancePreferences();
installWebVersionRefresh();
installPromotionQualification();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
