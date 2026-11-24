import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig, loadEnv } from "vite";

import { ENVIRONMENT_KEY, PUBLIC_ENV_PREFIX, validateBuildEnv } from "./src/core/env/build-env.ts";

const REPO_ROOT = path.resolve(import.meta.dirname, "../..");
const WEB_PORT = 3000;

export default defineConfig(({ mode }) => {
  validateBuildEnv(loadEnv(mode, REPO_ROOT, [PUBLIC_ENV_PREFIX, ENVIRONMENT_KEY]));
  return {
    envDir: REPO_ROOT,
    envPrefix: PUBLIC_ENV_PREFIX,
    plugins: [react(), tailwindcss()],
    resolve: { tsconfigPaths: true },
    server: { port: WEB_PORT, strictPort: true },
    preview: { port: WEB_PORT, strictPort: true },
  };
});
