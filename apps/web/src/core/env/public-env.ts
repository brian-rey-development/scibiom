import { z } from "zod";

const API_URL_ERROR = "NEXT_PUBLIC_SCIBIOM_API_URL must be an absolute http(s) URL";

const publicEnvSchema = z.object({
  NEXT_PUBLIC_SCIBIOM_API_URL: z.url({ protocol: /^https?$/u, error: API_URL_ERROR }),
});

export type PublicEnv = Readonly<{ apiUrl: string }>;

export function parsePublicEnv(source: Readonly<Record<string, string | undefined>>): PublicEnv {
  const result = publicEnvSchema.safeParse(source);
  if (!result.success) {
    throw new Error(result.error.issues.map((issue) => issue.message).join("; "));
  }
  return { apiUrl: result.data.NEXT_PUBLIC_SCIBIOM_API_URL };
}

export const publicEnv = parsePublicEnv({
  NEXT_PUBLIC_SCIBIOM_API_URL: process.env.NEXT_PUBLIC_SCIBIOM_API_URL,
});
