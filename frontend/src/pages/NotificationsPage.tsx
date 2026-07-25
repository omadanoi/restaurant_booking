import { myNotifications } from "../api/endpoints";
import { useApi } from "../hooks/useApi";

const TYPE_LABELS: Record<string, string> = {
  reservation_confirmed: "Reservation confirmed",
  reservation_reminder: "Upcoming reservation reminder",
  reservation_cancelled: "Reservation cancelled",
  table_ready: "Your table is ready",
  waitlist_update: "Waitlist update",
};

export function NotificationsPage() {
  const { data, loading, error } = useApi(() => myNotifications(), []);

  return (
    <>
      <h1>Notifications</h1>
      {error && <div className="error">{error}</div>}
      {loading && <p className="muted">Loading…</p>}
      {data && data.items.length === 0 && (
        <div className="empty">
          <h2>Nothing here yet</h2>
          <p className="muted">Booking confirmations and reminders will appear here.</p>
        </div>
      )}

      <div className="grid">
        {data?.items.map((n) => {
          const payload = n.payload as { start_time?: string; event?: string };
          return (
            <div key={n.id} className="card">
              <div className="row" style={{ justifyContent: "space-between" }}>
                <h3>
                  {TYPE_LABELS[n.type] ?? n.type}
                  {payload.event === "updated" ? " (updated)" : ""}
                </h3>
                <span className={`badge ${n.status}`}>{n.status}</span>
              </div>
              {payload.start_time && (
                <p className="muted">For {new Date(payload.start_time).toLocaleString()}</p>
              )}
              <p className="muted">
                Received {new Date(n.created_at).toLocaleString()} · via {n.channel}
              </p>
            </div>
          );
        })}
      </div>
    </>
  );
}
