import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { CompanionApp } from "./CompanionApp";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode><CompanionApp /></StrictMode>,
);
