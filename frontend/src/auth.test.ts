import { describe, expect, it } from "vitest";
import { profileName } from "./auth";

describe("auth profile helpers", () => {
  it("uses the first name for the user menu", () => {
    expect(profileName({ firstName: "Admin", username: "admin" })).toBe("Admin");
  });
  it("falls back to username and then operator", () => {
    expect(profileName({ username: "viewer" })).toBe("viewer");
    expect(profileName()).toBe("Operator");
  });
});
