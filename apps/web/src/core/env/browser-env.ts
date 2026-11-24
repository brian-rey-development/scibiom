import { parsePublicEnv } from "@core/env/public-env";

// Kept apart from public-env.ts because vite.config.ts imports that file in Node, where import.meta.env is undefined.
export const publicEnv = parsePublicEnv({
  VITE_SCIBIOM_API_URL: import.meta.env.VITE_SCIBIOM_API_URL,
});
