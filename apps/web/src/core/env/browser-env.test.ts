import { describe, expect, it } from "vitest";

import { publicEnv } from "@core/env/browser-env";

describe("publicEnv", () => {
  it("reads the API URL that Vite inlines into import.meta.env", () => {
    expect(publicEnv.apiUrl).toBe(import.meta.env.VITE_SCIBIOM_API_URL);
  });
});
