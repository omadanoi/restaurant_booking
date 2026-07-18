import { useMemo, useState } from "react";

import { ApiError } from "../api/client";
import {
  changeReservationStatus,
  changeTableStatus,
  listFloors,
  listTables,
  restaurantReservations,
} from "../api/endpoints";
import type { DiningTable, TableStatus } from "../api/types";
import { FloorCanvas, FloorLegend } from "../components/FloorCanvas";
import { useApi } from "../hooks/useApi";
import { useMyRestaurants } from "../hooks/useMyRestaurants";
import { useRestaurantEvents } from "../hooks/useRestaurantEvents";

const TABLE_ACTIONS: { status: TableStatus; label: string }[] = [
  { status: "occupied", label: "Seat / occupy" },
  { status: "cleaning", label: "Needs cleaning" },
  { status: "available", label: "Mark available" },
  { status: "out_of_service", label: "Out of service" },
];

const RESERVATION_ACTIONS: Record<string, { to: string; label: string }[]> = {
  pending: [
    { to: "confirmed", label: "Confirm" },
    { to: "cancelled", label: "Cancel" },
  ],
  confirmed: [
    { to: "seated", label: "Seat" },
    { to: "no_show", label: "No-show" },
    { to: "cancelled", label: "Cancel" },
  ],
  seated: [{ to: "completed", label: "Complete" }],
};

export function StaffDashboardPage() {
  const { restaurants, selected, selectedId, setSelectedId, loading } = useMyRestaurants();
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [selectedTable, setSelectedTable] = useState<DiningTable | null>(null);
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState<string | null>(null);

  const floorsApi = useApi(
    () => (selectedId ? listFloors(selectedId) : Promise.resolve([])),
    [selectedId],
  );
  const tablesApi = useApi(
    () => (selectedId ? listTables(selectedId) : Promise.resolve([])),
    [selectedId],
  );
  const reservationsApi = useApi(
    () =>
      selectedId
        ? restaurantReservations(selectedId, { on_date: date, limit: 100 })
        : Promise.resolve({ items: [], total: 0, limit: 0, offset: 0 }),
    [selectedId, date],
  );

  const [activeFloorId, setActiveFloorId] = useState<string | null>(null);
  const floors = floorsApi.data ?? [];
  const floor = floors.find((f) => f.id === activeFloorId) ?? floors[0] ?? null;
  const floorTables = useMemo(
    () => (tablesApi.data ?? []).filter((t) => t.floor_id === floor?.id),
    [tablesApi.data, floor],
  );

  // Live updates: refresh the affected data instead of tracking event
  // payload minutiae — simple and always consistent.
  useRestaurantEvents(selectedId, (event) => {
    setLive(`${event.type} · ${new Date().toLocaleTimeString()}`);
    if (event.type.startsWith("table.")) void tablesApi.reload();
    if (event.type.startsWith("reservation.")) void reservationsApi.reload();
  });

  async function setTableStatus(status: TableStatus) {
    if (!selectedId || !selectedTable) return;
    setError(null);
    try {
      await changeTableStatus(selectedId, selectedTable.id, status, note || undefined);
      setNote("");
      setSelectedTable(null);
      await tablesApi.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Status change failed.");
    }
  }

  async function moveReservation(id: string, to: string) {
    setError(null);
    try {
      await changeReservationStatus(id, to);
      await reservationsApi.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Transition failed.");
    }
  }

  if (loading) return <p className="muted">Loading…</p>;
  if (restaurants.length === 0) {
    return <p className="muted">You are not assigned to any restaurant yet.</p>;
  }

  return (
    <>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>Staff dashboard{selected ? ` — ${selected.name}` : ""}</h1>
        <div className="row">
          {live && <span className="muted">live: {live}</span>}
          {restaurants.length > 1 && (
            <select value={selectedId ?? ""} onChange={(e) => setSelectedId(e.target.value)}>
              {restaurants.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {floors.length > 1 && (
        <div className="row" style={{ margin: "0.75rem 0" }}>
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
        <div className="floor-wrap" style={{ marginTop: "0.5rem" }}>
          <FloorCanvas
            floor={floor}
            tables={floorTables}
            selectedId={selectedTable?.id ?? null}
            onSelect={(t) => setSelectedTable(t.id === selectedTable?.id ? null : t)}
          />
          <FloorLegend />
        </div>
      )}

      {selectedTable && (
        <div className="card" style={{ marginTop: "1rem" }}>
          <h2>
            Table {selectedTable.table_number} —{" "}
            <span className={`badge ${selectedTable.status}`}>{selectedTable.status}</span>
          </h2>
          <div className="row">
            {TABLE_ACTIONS.filter((a) => a.status !== selectedTable.status).map((a) => (
              <button key={a.status} onClick={() => setTableStatus(a.status)}>
                {a.label}
              </button>
            ))}
            <input
              placeholder="Note (optional)"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              style={{ flex: 1, minWidth: "180px" }}
            />
          </div>
        </div>
      )}

      <div className="row" style={{ margin: "1.5rem 0 0.5rem", justifyContent: "space-between" }}>
        <h2>Reservations</h2>
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
      </div>

      <div className="card">
        {reservationsApi.data && reservationsApi.data.items.length === 0 && (
          <p className="muted">No reservations for this day.</p>
        )}
        {reservationsApi.data && reservationsApi.data.items.length > 0 && (
          <table className="data">
            <thead>
              <tr>
                <th>Time</th>
                <th>Table</th>
                <th>Party</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {reservationsApi.data.items.map((r) => {
                const tableNumber =
                  tablesApi.data?.find((t) => t.id === r.table_id)?.table_number ?? "?";
                return (
                  <tr key={r.id}>
                    <td>
                      {new Date(r.start_time).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                      –
                      {new Date(r.end_time).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </td>
                    <td>{tableNumber}</td>
                    <td>{r.party_size}</td>
                    <td>
                      <span className={`badge ${r.status}`}>{r.status.replace("_", " ")}</span>
                    </td>
                    <td>
                      <div className="row">
                        {(RESERVATION_ACTIONS[r.status] ?? []).map((a) => (
                          <button
                            key={a.to}
                            className="small"
                            onClick={() => moveReservation(r.id, a.to)}
                          >
                            {a.label}
                          </button>
                        ))}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}
