import { describe, expect, it } from "vitest";
import { canAccess, canApprove } from "./permissions";

describe("role permissions", () => {
  it("allows Admin to access administration", () => {
    expect(canAccess(["Admin"], ["Admin"])).toBe(true);
  });
  it("denies Viewer access to administration", () => {
    expect(canAccess(["Viewer"], ["Admin"])).toBe(false);
  });
  it("only allows controller roles to approve", () => {
    expect(canApprove(["Viewer"])).toBe(false);
    expect(canApprove(["Inventory Controller"])).toBe(true);
  });
});
