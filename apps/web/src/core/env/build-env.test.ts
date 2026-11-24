import { describe, expect, it } from "vitest";

import { validateBuildEnv } from "@core/env/build-env";

const LOCAL_URL = "http://127.0.0.1:8000";
const PUBLIC_URL = "https://api.scibiom.test";
const HARDENED_ERROR = "must be an https URL with a public host in staging and production";

function buildEnv(environment: string | undefined, apiUrl: string) {
  return { SCIBIOM_ENVIRONMENT: environment, VITE_SCIBIOM_API_URL: apiUrl };
}

describe("validateBuildEnv API URL", () => {
  it.each(["local", "test"])("accepts a loopback http URL in %s", (environment) => {
    expect(validateBuildEnv(buildEnv(environment, LOCAL_URL)).apiUrl).toBe(LOCAL_URL);
  });

  it.each(["staging", "production"])("accepts a public https URL in %s", (environment) => {
    expect(validateBuildEnv(buildEnv(environment, PUBLIC_URL)).apiUrl).toBe(PUBLIC_URL);
  });

  it.each([
    "http://api.scibiom.test",
    "https://localhost:8000",
    "https://127.0.0.1",
    "https://[::1]:8000",
    "https://0.0.0.0",
    "https://api.localhost",
  ])("rejects %s in production", (apiUrl) => {
    expect(() => validateBuildEnv(buildEnv("production", apiUrl))).toThrow(HARDENED_ERROR);
  });
});

describe("validateBuildEnv guards", () => {
  it.each([undefined, "", "prod"])("rejects the environment %s", (environment) => {
    expect(() => validateBuildEnv(buildEnv(environment, LOCAL_URL))).toThrow(
      "SCIBIOM_ENVIRONMENT must be local, test, staging or production",
    );
  });

  it("rejects public variables outside the allowlist", () => {
    const source = { ...buildEnv("local", LOCAL_URL), VITE_SECRET_KEY: "leak" };
    expect(() => validateBuildEnv(source)).toThrow("VITE_SECRET_KEY");
  });
});
