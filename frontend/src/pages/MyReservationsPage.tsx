import { useState } from "react";

import { ApiError } from "../api/client";
import { cancelReservation, myReservations } from "../api/endpoints";
import { useApi } from "../hooks/useApi";

export function MyReservationsPage() {
  const { data, loading, error, reload } = useApi(() => myReservations(), []);
  const [actionError, setActionError] = useState<string | null>(null);

  async function cancel(id: string) {
    setActionError(null);
    try {
      await cancelReservation(id);
      await reload();
    } catch (err) {
      setActionError(err instanceof ApiError ? err.detail : "Could not cancel.");
    }
  }

  return (
    <>
      <h1>My reservations</h1>
      {error && <div className="error">{error}</div>}
      {actionError && <div className="error">{actionError}</div>}
      {loading && <p className="muted">Loading…</p>}

      {data && data.items.length === 0 && (
        <div className="empty">
          <h2>No reservations yet</h2>
          <p className="muted">Browse restaurants to book your first table.</p>
        </div>
      )}

      {data && data.items.length > 0 && (
        <div className="card">
          <table className="data">
            <thead>
              <tr>
                <th>When</th>
                <th>Until</th>
                <th>Party</th>
                <th>Requests</th>
                <th>Status</th>
                <th>Deposit</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.items.map((r) => {
                const cancellable = r.status === "pending" || r.status === "confirmed";
                return (
                  <tr key={r.id}>
                    <td>{new Date(r.start_time).toLocaleString()}</td>
                    <td>{new Date(r.end_time).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</td>
                    <td>{r.party_size}</td>
                    <td className="req-cell" title={r.special_requests ?? undefined}>
                      {r.special_requests ?? <span className="muted">—</span>}
                    </td>
                    <td>
                      <span className={`badge ${r.status}`}>{r.status.replace("_", " ")}</span>
                    </td>
                    <td>
                      {r.deposit_status !== "none" ? (
                        <span className={`badge ${r.deposit_status}`} title="Deposits are refunded when you cancel">
                          {r.deposit_amount} {r.deposit_currency} · {r.deposit_status}
                        </span>
                      ) : (
                        <span className="muted">—</span>
                      )}
                    </td>
                    <td>
                      {cancellable && (
                        <button className="small danger" onClick={() => cancel(r.id)}>
                          Cancel
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
