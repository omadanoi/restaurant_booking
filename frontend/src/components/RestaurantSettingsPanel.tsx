import { useEffect, useState } from "react";

import { ApiError } from "../api/client";
import { getRestaurant, updateRestaurant } from "../api/endpoints";
import { useApi } from "../hooks/useApi";
import { LocationPicker } from "./map/LocationPicker";

const CURRENCIES = ["USD", "EUR", "KGS", "RUB", "KZT"];

/** Manager settings: booking-deposit policy + map location pin. */
export function RestaurantSettingsPanel({ restaurantId }: { restaurantId: string }) {
  const { data: restaurant, reload } = useApi(() => getRestaurant(restaurantId), [restaurantId]);

  const [depositEnabled, setDepositEnabled] = useState(false);
  const [amount, setAmount] = useState("");
  const [currency, setCurrency] = useState("USD");
  const [cutoffHours, setCutoffHours] = useState(0);
  const [pin, setPin] = useState<{ lat: number; lng: number } | null>(null);
  const [message, setMessage] = useState<{ kind: "success" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  // Sync form state whenever the (re)loaded restaurant arrives.
  useEffect(() => {
    if (!restaurant) return;
    setDepositEnabled(restaurant.deposit_enabled);
    setAmount(restaurant.deposit_amount ?? "");
    setCurrency(restaurant.deposit_currency);
    setCutoffHours(restaurant.cancellation_cutoff_hours);
    setPin(
      restaurant.latitude !== null && restaurant.longitude !== null
        ? { lat: restaurant.latitude, lng: restaurant.longitude }
        : null,
    );
  }, [restaurant]);

  async function save() {
    setBusy(true);
    setMessage(null);
    try {
      await updateRestaurant(restaurantId, {
        deposit_enabled: depositEnabled,
        deposit_amount: amount === "" ? null : amount,
        deposit_currency: currency,
        cancellation_cutoff_hours: cutoffHours,
        latitude: pin?.lat ?? null,
        longitude: pin?.lng ?? null,
      });
      await reload();
      setMessage({ kind: "success", text: "Settings saved." });
    } catch (err) {
      setMessage({ kind: "error", text: err instanceof ApiError ? err.detail : "Save failed." });
    } finally {
      setBusy(false);
    }
  }

  if (!restaurant) return <p className="muted">Loading…</p>;

  return (
    <div className="card" style={{ marginTop: "1rem" }}>
      <h2>Booking deposits</h2>
      <p className="muted">
        Require a deposit when customers book. It's refunded automatically on cancellation and
        kept if the guest doesn't show up — this deters no-shows and prank bookings.
      </p>
      <div className="row">
        <label className="field" style={{ justifyContent: "end" }}>
          <span>
            <input
              type="checkbox"
              checked={depositEnabled}
              onChange={(e) => setDepositEnabled(e.target.checked)}
            />{" "}
            Require a deposit
          </span>
        </label>
        <label className="field">
          Amount
          <input
            type="number"
            min={0}
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            style={{ width: "7rem" }}
            disabled={!depositEnabled}
          />
        </label>
        <label className="field">
          Currency
          <select
            value={currency}
            onChange={(e) => setCurrency(e.target.value)}
            disabled={!depositEnabled}
          >
            {CURRENCIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </label>
      </div>

      <h2 style={{ marginTop: "1.25rem" }}>Cancellation policy</h2>
      <p className="muted">
        Customers can't cancel within this many hours of their reservation (staff always can).
        Combined with a deposit, this stops last-minute flake-outs. 0 = cancel anytime.
      </p>
      <label className="field" style={{ maxWidth: "12rem" }}>
        Cutoff (hours before start)
        <input
          type="number"
          min={0}
          max={168}
          value={cutoffHours}
          onChange={(e) => setCutoffHours(Math.max(0, Number(e.target.value)))}
        />
      </label>

      <h2 style={{ marginTop: "1.25rem" }}>Location on the map</h2>
      <p className="muted">
        Click the map to place the pin customers see when browsing restaurants.
      </p>
      <LocationPicker
        lat={pin?.lat ?? null}
        lng={pin?.lng ?? null}
        onChange={(lat, lng) => setPin({ lat, lng })}
      />
      <div className="row" style={{ marginTop: "0.5rem", alignItems: "center" }}>
        <span className="muted">
          {pin ? `Pin: ${pin.lat}, ${pin.lng}` : "No pin set — the restaurant won't appear on the map."}
        </span>
        {pin && (
          <button className="small" onClick={() => setPin(null)}>
            Clear pin
          </button>
        )}
      </div>

      <div className="row" style={{ marginTop: "1rem" }}>
        <button className="primary" onClick={save} disabled={busy}>
          {busy ? "Saving…" : "Save settings"}
        </button>
        {message && <div className={message.kind}>{message.text}</div>}
      </div>
    </div>
  );
}
