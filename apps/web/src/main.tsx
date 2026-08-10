import "./legacy-browser-polyfills";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { applyStoredAppearancePreferences } from "./appearance-preferences";

applyStoredAppearancePreferences();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
