import { expect, test } from "@playwright/test";

import { API, DEMO_PASSWORD, apiLogin, futureDate, loginViaUi } from "./helpers";

test("role guard: customer cannot open the admin panel", async ({ page }) => {
  await loginViaUi(page, "customer@demo.com", DEMO_PASSWORD);
  await page.goto("/admin");
  // Redirected away by the role guard, back to the customer home.
  await expect(page).toHaveURL(/\/restaurants/);
});

test("waiter sees the staff dashboard with the live floor", async ({ page }) => {
  await loginViaUi(page, "waiter@demo.com", DEMO_PASSWORD);
  await expect(page).toHaveURL(/\/staff/);
  await expect(page.getByRole("heading", { name: /Staff dashboard/ })).toBeVisible();
  await expect(page.locator("g.floor-table").first()).toBeVisible();
  // Waiters get no floor-editor nav entry.
  await expect(page.getByRole("link", { name: "Floor editor" })).toHaveCount(0);
});

test("manager drags a table and the new position is persisted", async ({ page, request }) => {
  // The drag PERSISTS to the database, so without cleanup each run pushes
  // the table further until it drifts out of the viewport and the mouse
  // misses it entirely. Snapshot the layout first and restore it at the end.
  const restaurants = (await (await request.get(`${API}/restaurants`)).json()) as {
    items: { id: string; name: string }[];
  };
  const demo = restaurants.items.find((r) => r.name === "Trattoria Demo")!;
  const tablesBefore = (await (
    await request.get(`${API}/restaurants/${demo.id}/tables`)
  ).json()) as { id: string; x: number; y: number }[];

  await loginViaUi(page, "manager@demo.com", DEMO_PASSWORD);
  await page.goto("/editor");

  const table = page.locator("g.floor-table").first();
  await expect(table).toBeVisible();
  const before = await table.getAttribute("transform");

  // Ensure the drag target is inside the viewport before grabbing its
  // coordinates — mouse events outside the window hit nothing.
  await table.scrollIntoViewIfNeeded();
  const box = (await table.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 80, box.y + box.height / 2 + 50, { steps: 8 });
  await page.mouse.up();

  await expect(page.getByText("Position saved")).toBeVisible();

  // Reload: the moved position came back from the database, not local state.
  await page.reload();
  const after = await page.locator("g.floor-table").first().getAttribute("transform");
  expect(after).not.toBe(before);

  // Restore the original layout so repeated runs stay deterministic.
  const token = await apiLogin(request, "manager@demo.com", DEMO_PASSWORD);
  const tablesAfter = (await (
    await request.get(`${API}/restaurants/${demo.id}/tables`)
  ).json()) as { id: string; x: number; y: number }[];
  for (const t of tablesAfter) {
    const orig = tablesBefore.find((o) => o.id === t.id);
    if (orig && (orig.x !== t.x || orig.y !== t.y)) {
      await request.patch(`${API}/restaurants/${demo.id}/tables/${t.id}`, {
        headers: { Authorization: `Bearer ${token}` },
        data: { x: orig.x, y: orig.y },
      });
    }
  }
});

test("waiter dashboard receives a live event when a customer books", async ({
  page,
  request,
}) => {
  await loginViaUi(page, "waiter@demo.com", DEMO_PASSWORD);
  await expect(page.locator("g.floor-table").first()).toBeVisible();
  // Give the dashboard's websocket a beat to finish connecting.
  await page.waitForTimeout(1500);

  // A customer books via the API (separate session, like another device).
  const token = await apiLogin(request, "customer@demo.com", DEMO_PASSWORD);
  const restaurants = (await (await request.get(`${API}/restaurants`)).json()) as {
    items: { id: string; name: string }[];
  };
  const restaurant = restaurants.items.find((r) => r.name === "Trattoria Demo")!;

  const start = new Date(`${futureDate()}T18:00:00-04:00`);
  const end = new Date(start.getTime() + 90 * 60_000);
  const availability = (await (
    await request.get(
      `${API}/restaurants/${restaurant.id}/availability?start_time=${encodeURIComponent(
        start.toISOString(),
      )}&end_time=${encodeURIComponent(end.toISOString())}&party_size=2`,
    )
  ).json()) as { id: string }[];
  expect(availability.length).toBeGreaterThan(0);

  const created = await request.post(`${API}/reservations`, {
    headers: { Authorization: `Bearer ${token}` },
    data: {
      table_id: availability[0].id,
      start_time: start.toISOString(),
      end_time: end.toISOString(),
      party_size: 2,
    },
  });
  expect(created.status()).toBe(201);

  // The waiter's open dashboard reflects the event over the websocket.
  await expect(page.getByText(/live: reservation\.created/)).toBeVisible({ timeout: 15_000 });
});
