import { describe, expect, it } from "vitest";
import { ApiError } from "./api";

describe("API error contract", () => {
  it("preserves RFC 7807 detail and status", () => {
    const error = new ApiError({ title: "Forbidden", detail: "Site access denied" }, 403);
    expect(error.problem.status).toBe(403);
    expect(error.message).toBe("Site access denied");
  });
});
