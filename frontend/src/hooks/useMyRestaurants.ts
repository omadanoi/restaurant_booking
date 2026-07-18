import { useEffect, useState } from "react";

import { api } from "../api/client";
import type { Restaurant } from "../api/types";

/** Restaurants the current staff user may operate on, plus a selection. */
export function useMyRestaurants() {
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api<Restaurant[]>("/users/me/restaurants")
      .then((items) => {
        setRestaurants(items);
        setSelectedId((current) => current ?? items[0]?.id ?? null);
      })
      .finally(() => setLoading(false));
  }, []);

  const selected = restaurants.find((r) => r.id === selectedId) ?? null;
  return { restaurants, selected, selectedId, setSelectedId, loading };
}
