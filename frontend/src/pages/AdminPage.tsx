import { useState, type FormEvent } from "react";

import { ApiError } from "../api/client";
import { createRestaurant, listRestaurants, listUsers, suspendRestaurant } from "../api/endpoints";
import { useApi } from "../hooks/useApi";

export function AdminPage() {
  const restaurantsApi = useApi(() => listRestaurants({ limit: 100 }), []);
  const usersApi = useApi(() => listUsers({ limit: 100 }), []);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    address: "",
    city: "",
    country: "",
    timezone: "UTC",
    cuisine_type: "",
  });

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createRestaurant({ ...form, cuisine_type: form.cuisine_type || null });
      setForm({ name: "", address: "", city: "", country: "", timezone: "UTC", cuisine_type: "" });
      await restaurantsApi.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not create restaurant.");
    }
  }

  async function suspend(id: string) {
    setError(null);
    try {
      await suspendRestaurant(id);
      await restaurantsApi.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not suspend restaurant.");
    }
  }

  return (
    <>
      <h1>Administration</h1>
      {error && <div className="error">{error}</div>}

      <div className="card" style={{ margin: "1rem 0" }}>
        <h2>New restaurant</h2>
        <form className="row" onSubmit={handleCreate}>
          {(
            [
              ["name", "Name"],
              ["address", "Address"],
              ["city", "City"],
              ["country", "Country"],
              ["timezone", "Timezone (IANA)"],
              ["cuisine_type", "Cuisine"],
            ] as const
          ).map(([key, label]) => (
            <label key={key} className="field">
              {label}
              <input
                value={form[key]}
                onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                required={key !== "cuisine_type"}
                style={{ width: "10rem" }}
              />
            </label>
          ))}
          <button className="primary" style={{ alignSelf: "end" }}>
            Create
          </button>
        </form>
      </div>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <h2>Restaurants</h2>
        <table className="data">
          <thead>
            <tr>
              <th>Name</th>
              <th>City</th>
              <th>Active</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {restaurantsApi.data?.items.map((r) => (
              <tr key={r.id}>
                <td>{r.name}</td>
                <td>{r.city}</td>
                <td>{r.is_active ? "yes" : "no"}</td>
                <td>
                  {r.is_active && (
                    <button className="small danger" onClick={() => suspend(r.id)}>
                      Suspend
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h2>Users ({usersApi.data?.total ?? "…"})</h2>
        <table className="data">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Active</th>
            </tr>
          </thead>
          <tbody>
            {usersApi.data?.items.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name}</td>
                <td>{u.email}</td>
                <td>
                  <span className="badge confirmed">{u.role}</span>
                </td>
                <td>{u.is_active ? "yes" : "no"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
