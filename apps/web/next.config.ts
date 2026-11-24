import { loadEnvConfig } from "@next/env";
import type { NextConfig } from "next";
import path from "node:path";

const REPO_ROOT = path.resolve(import.meta.dirname, "../..");
const IS_DEV = process.env.NODE_ENV === "development";

async function buildConfig(): Promise<NextConfig> {
  // @next/env caches its first call, which Next already made for apps/web, so a plain call is a no-op.
  loadEnvConfig(REPO_ROOT, IS_DEV, console, true);
  // Imported after the env load because public-env.ts validates process.env when it is evaluated.
  const { parsePublicEnv } = await import("./src/core/env/public-env.ts");
  parsePublicEnv(process.env);
  return {};
}

export default buildConfig;
