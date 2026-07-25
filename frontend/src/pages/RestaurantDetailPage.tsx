import { useMemo, useState } from "react";
import { useParams } from "react-router-dom";

import { ApiError } from "../api/client";
import {
  createReservation,
  findAvailability,
  getOpeningHours,
  getRestaurant,
  listElements,
  listFloors,
  listTables,
} from "../api/endpoints";
import type { DiningTable } from "../api/types";
import { FloorCanvas, FloorLegend } from "../components/FloorCanvas";
import { RestaurantMiniMap } from "../components/map/RestaurantMiniMap";
import { useApi } from "../hooks/useApi";

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function defaultDate(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}

export function RestaurantDetailPage() {
  const { id } = useParams<{ id: string }>();
  const restaurantId = id!;

  const { data: restaurant } = useApi(() => getRestaurant(restaurantId), [restaurantId]);
  const { data: floors } = useApi(() => listFloors(restaurantId), [restaurantId]);
  const { data: tables } = useApi(() => listTables(restaurantId), [restaurantId]);
  const { data: elements } = useApi(() => listElements(restaurantId), [restaurantId]);
  const { data: hours } = useApi(() => getOpeningHours(restaurantId), [restaurantId]);

  const [activeFloorId, setActiveFloorId] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    date: defaultDate(),
    time: "18:00",
    duration: "90",
    partySize: 2,
    accessibleOnly: false,
  });
  const [available, setAvailable] = useState<Set<string> | null>(null);
  const [selected, setSelected] = useState<DiningTable | null>(null);
  const [requests, setRequests] = useState("");
  // Demo payment form; prefilled with the classic always-succeeds test card.
  const [card, setCard] = useState({ number: "4242 4242 4242 4242", expiry: "", cvc: "" });
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  const floor = useMemo(() => {
    if (!floors || floors.length === 0) return null;
    return floors.find((f) => f.id === activeFloorId) ?? floors[0];
  }, [floors, activeFloorId]);

  const floorTables = useMemo(
    () => (tables ?? []).filter((t) => t.floor_id === floor?.id),
    [tables, floor],
  );
  const floorElements = useMemo(
    () => (elements ?? []).filter((e) => e.floor_id === floor?.id),
    [elements, floor],
  );

  function window(): { start: Date; end: Date } {
    const start = new Date(`${filters.date}T${filters.time}:00`);
    const end = new Date(start.getTime() + Number(filters.duration) * 60_000);
    return { start, end };
  }

  async function checkAvailability() {
    setBusy(true);
    setMessage(null);
    setSelected(null);
    try {
      const { start, end } = window();
      const result = await findAvailability(restaurantId, {
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        party_size: filters.partySize,
        accessible: filters.accessibleOnly || undefined,
      });
      setAvailable(new Set(result.map((t) => t.id)));
      if (result.length === 0) {
        setMessage({ kind: "error", text: "No tables available for that time and party size." });
      }
    } catch (err) {
      setMessage({
        kind: "error",
        text: err instanceof ApiError ? err.detail : "Could not check availability.",
      });
    } finally {
      setBusy(false);
    }
  }

  const depositDue =
    restaurant?.deposit_enabled && restaurant.deposit_amount
      ? `${restaurant.deposit_amount} ${restaurant.deposit_currency}`
      : null;

  async function book() {
    if (!selected) return;
    setBusy(true);
    setMessage(null);
    try {
      const { start, end } = window();
      await createReservation({
        table_id: selected.id,
        start_time: start.toISOString(),
        end_time: end.toISOString(),
        party_size: filters.partySize,
        special_requests: requests || undefined,
        payment: depositDue ? { card_number: card.number } : undefined,
      });
      setMessage({
        kind: "success",
        text: depositDue
          ? `Booked table ${selected.table_number} on ${filters.date} at ${filters.time} — ${depositDue} deposit paid (refunded if you cancel). See "My reservations".`
          : `Booked table ${selected.table_number} on ${filters.date} at ${filters.time}. See "My reservations".`,
      });
      setSelected(null);
      setAvailable(null);
    } catch (err) {
      setMessage({
        kind: "error",
        text: err instanceof ApiError ? err.detail : "Booking failed.",
      });
    } finally {
      setBusy(false);
    }
  }

  if (!restaurant) return <p className="muted">Loading…</p>;

  return (
    <>
      <h1>{restaurant.name}</h1>
      <p className="muted">
        {restaurant.cuisine_type} · {restaurant.address}, {restaurant.city} · timezone{" "}
        {restaurant.timezone}
      </p>

      {hours && hours.length > 0 && (
        <p className="muted">
          Hours:{" "}
          {hours
            .map((h) =>
              h.is_closed
                ? `${DAYS[h.day_of_week]} closed`
                : `${DAYS[h.day_of_week]} ${h.opens_at?.slice(0, 5)}–${h.closes_at?.slice(0, 5)}`,
            )
            .join(" · ")}
        </p>
      )}

      {restaurant.latitude !== null && restaurant.longitude !== null && (
        <div className="card map-card" style={{ margin: "1rem 0" }}>
          <RestaurantMiniMap lat={restaurant.latitude} lng={restaurant.longitude} />
        </div>
      )}

      <div className="card" style={{ margin: "1rem 0" }}>
        <div className="row">
          <label className="field">
            Date
            <input
              type="date"
              value={filters.date}
              onChange={(e) => setFilters((f) => ({ ...f, date: e.target.value }))}
            />
          </label>
          <label className="field">
            Time
            <input
              type="time"
              value={filters.time}
              onChange={(e) => setFilters((f) => ({ ...f, time: e.target.value }))}
            />
          </label>
          <label className="field">
            Duration
            <select
              value={filters.duration}
              onChange={(e) => setFilters((f) => ({ ...f, duration: e.target.value }))}
            >
              <option value="60">1 hour</option>
              <option value="90">1.5 hours</option>
              <option value="120">2 hours</option>
              <option value="180">3 hours</option>
            </select>
          </label>
          <label className="field">
            Party size
            <input
              type="number"
              min={1}
              max={50}
              value={filters.partySize}
              onChange={(e) => setFilters((f) => ({ ...f, partySize: Number(e.target.value) }))}
              style={{ width: "5rem" }}
            />
          </label>
          <label className="field" style={{ justifyContent: "end" }}>
            <span>
              <input
                type="checkbox"
                checked={filters.accessibleOnly}
                onChange={(e) => setFilters((f) => ({ ...f, accessibleOnly: e.target.checked }))}
              />{" "}
              Accessible only
            </span>
          </label>
          <button className="primary" onClick={checkAvailability} disabled={busy}>
            Check availability
          </button>
        </div>
      </div>

      {message && <div className={message.kind}>{message.text}</div>}

      {floors && floors.length > 1 && (
        <div className="row" style={{ marginBottom: "0.75rem" }}>
          {floors.map((f) => (
            <button
              key={f.id}
              className={f.id === floor?.id ? "primary" : ""}
              onClick={() => setActiveFloorId(f.id)}
            >
              {f.name}
            </button>
          ))}
        </div>
      )}

      {floor && (
        <div className="floor-wrap">
          <FloorCanvas
            floor={floor}
            tables={floorTables}
            elements={floorElements}
            selectableIds={available}
            selectedId={selected?.id ?? null}
            onSelect={(t) => setSelected(t)}
          />
          <FloorLegend />
        </div>
      )}
      {available === null && (
        <p className="muted" style={{ marginTop: "0.5rem" }}>
          Pick a date, time and party size, then check availability to select a table.
        </p>
      )}

      {selected && (
        <div className="card" style={{ marginTop: "1rem" }}>
          <h2>
            Book table {selected.table_number} ({selected.capacity} seats,{" "}
            {selected.is_indoor ? "indoor" : "outdoor"})
          </h2>
          <div className="row">
            <input
              placeholder="Special requests (optional)"
              value={requests}
              onChange={(e) => setRequests(e.target.value)}
              style={{ flex: 1, minWidth: "240px" }}
            />
          </div>
          {restaurant.cancellation_cutoff_hours > 0 && (
            <p className="muted" style={{ marginTop: "0.5rem" }}>
              Free cancellation until {restaurant.cancellation_cutoff_hours}h before your
              reservation; after that, contact the restaurant.
            </p>
          )}
          {depositDue && (
            <div className="deposit-box">
              <p>
                <strong>{depositDue} deposit</strong> — fully refunded if you cancel, kept by
                the restaurant if you don't show up.
              </p>
              <div className="row">
                <label className="field" style={{ flex: 2, minWidth: "180px" }}>
                  Card number
                  <input
                    value={card.number}
                    onChange={(e) => setCard((c) => ({ ...c, number: e.target.value }))}
                    autoComplete="off"
                  />
                </label>
                <label className="field" style={{ width: "6rem" }}>
                  MM/YY
                  <input
                    placeholder="12/28"
                    value={card.expiry}
                    onChange={(e) => setCard((c) => ({ ...c, expiry: e.target.value }))}
                    autoComplete="off"
                  />
                </label>
                <label className="field" style={{ width: "5rem" }}>
                  CVC
                  <input
                    placeholder="123"
                    value={card.cvc}
                    onChange={(e) => setCard((c) => ({ ...c, cvc: e.target.value }))}
                    autoComplete="off"
                  />
                </label>
              </div>
              <p className="muted" style={{ marginTop: "0.25rem" }}>
                Demo payments — no real charge. Any card works; one ending in 0002 is declined.
              </p>
            </div>
          )}
          <div className="row" style={{ marginTop: "0.75rem" }}>
            <button className="primary" onClick={book} disabled={busy}>
              {busy
                ? "Booking…"
                : depositDue
                  ? `Pay ${depositDue} & confirm for ${filters.date} ${filters.time}`
                  : `Confirm for ${filters.date} ${filters.time}`}
            </button>
          </div>
        </div>
      )}
    </>
  );
}
