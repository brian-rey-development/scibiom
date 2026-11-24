import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./app";

const ROOT_SELECTOR = "#root";

const rootElement = document.querySelector(ROOT_SELECTOR);
if (rootElement === null) {
  throw new Error(`Missing ${ROOT_SELECTOR} element in index.html`);
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
