import { LatLngBounds } from "leaflet";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import { Link } from "react-router-dom";

import type { Restaurant } from "../../api/types";
import { TILE_ATTRIBUTION, TILE_URL } from "./leafletSetup";

/** Browse-page map: every restaurant with a pin, fitted to show them all. */
export function RestaurantsMap({ restaurants }: { restaurants: Restaurant[] }) {
  const located = restaurants.filter((r) => r.latitude !== null && r.longitude !== null);
  if (located.length === 0) return null;

  const bounds = new LatLngBounds(
    located.map((r) => [r.latitude!, r.longitude!] as [number, number]),
  );

  return (
    <MapContainer
      bounds={bounds}
      boundsOptions={{ padding: [40, 40], maxZoom: 14 }}
      scrollWheelZoom={false}
      className="restaurants-map"
    >
      <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
      {located.map((r) => (
        <Marker key={r.id} position={[r.latitude!, r.longitude!]}>
          <Popup>
            <strong>{r.name}</strong>
            {r.cuisine_type && <div>{r.cuisine_type}</div>}
            <div>{r.address}</div>
            <Link to={`/restaurants/${r.id}`}>View &amp; book</Link>
          </Popup>
        </Marker>
      ))}
    </MapContainer>
  );
}
