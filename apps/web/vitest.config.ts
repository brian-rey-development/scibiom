import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: { tsconfigPaths: true },
  test: {
    include: ["src/**/*.test.{ts,tsx}"],
    env: { VITE_SCIBIOM_API_URL: "http://127.0.0.1:8000" },
  },
});
