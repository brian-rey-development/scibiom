import { z } from "zod";

import { PUBLIC_ENV_KEYS, type PublicEnv, parsePublicEnv } from "./public-env";

export const PUBLIC_ENV_PREFIX = "VITE_";
export const ENVIRONMENT_KEY = "SCIBIOM_ENVIRONMENT";

const ENVIRONMENT_ERROR = `${ENVIRONMENT_KEY} must be local, test, staging or production`;
const HARDENED_API_URL_ERROR =
  "VITE_SCIBIOM_API_URL must be an https URL with a public host in staging and production";
const HARDENED_ENVIRONMENTS: ReadonlySet<string> = new Set(["staging", "production"]);
const HTTPS_PROTOCOL = "https:";
const LOOPBACK_HOSTNAMES: ReadonlySet<string> = new Set(["localhost", "[::1]", "0.0.0.0"]);
const LOOPBACK_IPV4_PREFIX = "127.";
const LOCALHOST_SUFFIX = ".localhost";

const environmentSchema = z.enum(["local", "test", "staging", "production"]);

type EnvSource = Readonly<Record<string, string | undefined>>;

export function validateBuildEnv(source: EnvSource): PublicEnv {
  rejectUnknownPublicKeys(source);
  const environment = parseEnvironment(source[ENVIRONMENT_KEY]);
  const publicEnv = parsePublicEnv(source);
  if (HARDENED_ENVIRONMENTS.has(environment) && !isPublicHttpsUrl(publicEnv.apiUrl)) {
    throw new Error(HARDENED_API_URL_ERROR);
  }
  return publicEnv;
}

function parseEnvironment(value: string | undefined): string {
  const result = environmentSchema.safeParse(value);
  if (!result.success) {
    throw new Error(ENVIRONMENT_ERROR);
  }
  return result.data;
}

function rejectUnknownPublicKeys(source: EnvSource): void {
  const unknownKeys = Object.keys(source).filter(
    (key) => key.startsWith(PUBLIC_ENV_PREFIX) && !PUBLIC_ENV_KEYS.includes(key),
  );
  if (unknownKeys.length > 0) {
    throw new Error(
      `Unknown public variables would ship to every browser: ${unknownKeys.join(", ")}`,
    );
  }
}

function isPublicHttpsUrl(value: string): boolean {
  const { protocol, hostname } = new URL(value);
  return protocol === HTTPS_PROTOCOL && !isLoopbackHostname(hostname);
}

function isLoopbackHostname(hostname: string): boolean {
  return (
    LOOPBACK_HOSTNAMES.has(hostname) ||
    hostname.startsWith(LOOPBACK_IPV4_PREFIX) ||
    hostname.endsWith(LOCALHOST_SUFFIX)
  );
}
