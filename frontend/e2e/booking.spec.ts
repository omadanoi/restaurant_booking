import { expect, test, type Page } from "@playwright/test";

import { futureDate, registerViaUi, uniqueEmail } from "./helpers";

async function openDemoRestaurant(page: Page): Promise<void> {
  await page.goto("/restaurants");
  await page.getByRole("heading", { name: "Trattoria Demo" }).click();
  await expect(page.getByRole("heading", { name: "Trattoria Demo" })).toBeVisible();
}

async function checkAvailability(page: Page, date: string, time = "18:00"): Promise<void> {
  await page.getByLabel("Date").fill(date);
  await page.getByLabel("Time").fill(time);
  await page.getByLabel("Party size").fill("2");
  await page.getByRole("button", { name: "Check availability" }).click();
}

function selectableTables(page: Page) {
  return page.locator("g.floor-table:not(.dimmed)");
}

test("customer books a table on the floor plan, then cancels it", async ({ page }) => {
  await registerViaUi(page, uniqueEmail("booker"));
  await openDemoRestaurant(page);

  const date = futureDate();
  await checkAvailability(page, date);

  // Tables render from DB coordinates; at least one is available.
  await expect(selectableTables(page).first()).toBeVisible();
  const before = await selectableTables(page).count();

  await selectableTables(page).first().click();
  await expect(page.getByRole("heading", { name: /Book table/ })).toBeVisible();
  await page.getByRole("button", { name: /Confirm for/ }).click();
  await expect(page.getByText(/Booked table/)).toBeVisible();

  // The same window now has one fewer available table.
  await checkAvailability(page, date);
  await expect(selectableTables(page)).toHaveCount(before - 1);

  // It shows up in the history, and can be cancelled.
  await page.getByRole("link", { name: "My reservations" }).click();
  await expect(page.locator("table.data tbody tr")).toHaveCount(1);
  await expect(page.locator(".badge.confirmed")).toBeVisible();
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page.locator(".badge.cancelled")).toBeVisible();

  // Cancelling frees the slot again.
  await openDemoRestaurant(page);
  await checkAvailability(page, date);
  await expect(selectableTables(page)).toHaveCount(before);
});

test("booking outside opening hours is rejected with a clear error", async ({ page }) => {
  await registerViaUi(page, uniqueEmail("nighthawk"));
  await openDemoRestaurant(page);

  // 21:30 + 90min ends 23:00, past the 22:00 close — the booking attempt
  // must fail with the opening-hours validation message from the backend.
  // (22:30 would trip a different guard: the window would cross midnight.)
  await checkAvailability(page, futureDate(), "21:30");
  await selectableTables(page).first().click();
  await page.getByRole("button", { name: /Confirm for/ }).click();
  await expect(page.getByText(/within opening hours/i)).toBeVisible();
});
