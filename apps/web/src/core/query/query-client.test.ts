import { describe, expect, it } from "vitest";

import { createQueryClient } from "@core/query/query-client";

describe("createQueryClient", () => {
  it("returns an independent client on every call", () => {
    expect(createQueryClient()).not.toBe(createQueryClient());
  });
});
