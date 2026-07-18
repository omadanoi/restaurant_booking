import { useState } from "react";
import { Link } from "react-router-dom";

import { listRestaurants } from "../api/endpoints";
import { useApi } from "../hooks/useApi";

export function RestaurantsPage() {
  const [city, setCity] = useState("");
  const [search, setSearch] = useState("");
  const { data, loading, error } = useApi(
    () => listRestaurants({ city: search || undefined }),
    [search],
  );

  return (
    <>
      <div className="row" style={{ justifyContent: "space-between", marginBottom: "1rem" }}>
        <h1>Restaurants</h1>
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            setSearch(city.trim());
          }}
        >
          <input
            placeholder="Filter by city…"
            value={city}
            onChange={(e) => setCity(e.target.value)}
          />
          <button>Search</button>
        </form>
      </div>

      {error && <div className="error">{error}</div>}
      {loading && <p className="muted">Loading…</p>}

      <div className="grid cols-3">
        {data?.items.map((r) => (
          <Link key={r.id} to={`/restaurants/${r.id}`} style={{ textDecoration: "none" }}>
            <div className="card">
              <h2>{r.name}</h2>
              <p className="muted">
                {r.cuisine_type ?? "Restaurant"} · {r.city}, {r.country}
              </p>
              <p className="muted">{r.description}</p>
            </div>
          </Link>
        ))}
      </div>
      {data && data.items.length === 0 && <p className="muted">No restaurants found.</p>}
    </>
  );
}
