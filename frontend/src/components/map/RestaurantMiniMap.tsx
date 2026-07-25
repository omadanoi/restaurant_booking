import { MapContainer, Marker, TileLayer } from "react-leaflet";

import { TILE_ATTRIBUTION, TILE_URL } from "./leafletSetup";

/** Small static locator map for a single restaurant's detail page. */
export function RestaurantMiniMap({ lat, lng }: { lat: number; lng: number }) {
  return (
    <MapContainer
      center={[lat, lng]}
      zoom={15}
      scrollWheelZoom={false}
      dragging={false}
      doubleClickZoom={false}
      zoomControl={false}
      className="mini-map"
    >
      <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
      <Marker position={[lat, lng]} />
    </MapContainer>
  );
}
