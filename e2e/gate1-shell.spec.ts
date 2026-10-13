import { expect, test } from "@playwright/test";

test("login page and SPA routes are reachable", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("heading", { name: "DRIMS" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in" })).toBeVisible();
  await page.goto("/unknown-route");
  await expect(page).toHaveURL(/\/login$/);
});

test("nginx serves health and the protected shell redirects unauthenticated users", async ({ page }) => {
  const response = await page.request.get("/healthz");
  expect(response.status()).toBe(200);
  await page.goto("/administration");
  await expect(page).toHaveURL(/\/login$/);
});
