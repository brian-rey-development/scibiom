import "@fontsource-variable/geist";

import { AppProviders } from "@core/providers/app-providers";

import { HomePage } from "./home-page";

import "./globals.css";

export function App() {
  return (
    <AppProviders>
      <HomePage />
    </AppProviders>
  );
}
