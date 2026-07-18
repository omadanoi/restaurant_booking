import { expect, test } from "@playwright/test";

import { DEMO_PASSWORD, loginViaUi, registerViaUi, uniqueEmail } from "./helpers";

test("new customer can register and lands on restaurant browsing", async ({ page }) => {
  await registerViaUi(page, uniqueEmail("register"));
  await expect(page.getByRole("heading", { name: "Restaurants" })).toBeVisible();
  // The nav reflects the customer role.
  await expect(page.getByRole("link", { name: "My reservations" })).toBeVisible();
});

test("login with wrong password shows an error and stays on login", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("customer@demo.com");
  await page.getByLabel("Password", { exact: true }).fill("definitely-wrong");
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page.getByText("Incorrect email or password.")).toBeVisible();
  await expect(page).toHaveURL(/\/login/);
});

test("signing out returns to the login page", async ({ page }) => {
  await loginViaUi(page, "customer@demo.com", DEMO_PASSWORD);
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/login/);
});
