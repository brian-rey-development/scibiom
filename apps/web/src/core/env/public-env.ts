import { z } from "zod";

const API_URL_ERROR = "VITE_SCIBIOM_API_URL must be an absolute http(s) URL";

const publicEnvSchema = z.object({
  VITE_SCIBIOM_API_URL: z.url({ protocol: /^https?$/u, error: API_URL_ERROR }),
});

export const PUBLIC_ENV_KEYS: readonly string[] = publicEnvSchema.keyof().options;

export type PublicEnv = Readonly<{ apiUrl: string }>;

export function parsePublicEnv(source: Readonly<Record<string, string | undefined>>): PublicEnv {
  const result = publicEnvSchema.safeParse(source);
  if (!result.success) {
    throw new Error(result.error.issues.map((issue) => issue.message).join("; "));
  }
  return { apiUrl: result.data.VITE_SCIBIOM_API_URL };
}
