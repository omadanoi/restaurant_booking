import { expect, type APIRequestContext, type Page } from "@playwright/test";

export const API = "http://127.0.0.1:8000/api/v1";
export const DEMO_PASSWORD = "Password123";

export function uniqueEmail(prefix: string): string {
  // example.com, not a .test TLD — the backend's email validation rejects
  // special-use/reserved domains (verified: that's real validation working).
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 10_000)}@example.com`;
}

/** A future date that is NOT a Monday (the demo restaurant closes Mondays),
 * offset randomly so repeated runs against the same dev DB don't collide.
 */
export function futureDate(): string {
  // All arithmetic in UTC so the weekday check matches the yyyy-mm-dd string
  // we return (mixing local getDay() with toISOString() can shift a day and
  // let a closed Monday slip through).
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + 30 + Math.floor(Math.random() * 300));
  if (d.getUTCDay() === 1) d.setUTCDate(d.getUTCDate() + 1);
  return d.toISOString().slice(0, 10);
}

export async function loginViaUi(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).not.toHaveURL(/\/login/);
}

export async function registerViaUi(page: Page, email: string): Promise<void> {
  await page.goto("/register");
  await page.getByLabel("Full name").fill("E2E Customer");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel(/^Password/).fill(DEMO_PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page).toHaveURL(/\/restaurants/);
}

/** API-side login (form-encoded, mirroring the SPA) for test setup steps. */
export async function apiLogin(
  request: APIRequestContext,
  email: string,
  password: string,
): Promise<string> {
  const resp = await request.post(`${API}/auth/login`, {
    form: { username: email, password },
  });
  expect(resp.ok()).toBeTruthy();
  return ((await resp.json()) as { access_token: string }).access_token;
}
