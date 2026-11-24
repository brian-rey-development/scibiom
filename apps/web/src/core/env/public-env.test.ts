import { describe, expect, it } from "vitest";

import { parsePublicEnv } from "@core/env/public-env";

const API_URL_KEY = "VITE_SCIBIOM_API_URL";
const EXPECTED_ERROR = `${API_URL_KEY} must be an absolute http(s) URL`;

describe("parsePublicEnv", () => {
  it.each(["http://127.0.0.1:8000", "https://api.scibiom.test"])("accepts %s", (url) => {
    expect(parsePublicEnv({ [API_URL_KEY]: url }).apiUrl).toBe(url);
  });

  it.each([
    ["missing", undefined],
    ["empty", ""],
    ["not a URL", "not a url"],
    ["relative", "/api"],
    ["a non-http scheme", "ftp://example.test"],
    ["a script scheme", "javascript:alert(1)"],
  ])("rejects a value that is %s", (_label, value) => {
    expect(() => parsePublicEnv({ [API_URL_KEY]: value })).toThrow(EXPECTED_ERROR);
  });
});
