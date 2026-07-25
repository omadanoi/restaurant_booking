import { MapContainer, Marker, TileLayer, useMapEvents } from "react-leaflet";

import { TILE_ATTRIBUTION, TILE_URL } from "./leafletSetup";

// Somewhere sensible to start when a restaurant has no pin yet.
const DEFAULT_CENTER: [number, number] = [42.8746, 74.5698]; // Bishkek
const DEFAULT_ZOOM = 12;

function ClickHandler({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e) {
      onPick(Number(e.latlng.lat.toFixed(6)), Number(e.latlng.lng.toFixed(6)));
    },
  });
  return null;
}

/** Manager settings map: click anywhere to place/move the restaurant pin. */
export function LocationPicker({
  lat,
  lng,
  onChange,
}: {
  lat: number | null;
  lng: number | null;
  onChange: (lat: number, lng: number) => void;
}) {
  const hasPin = lat !== null && lng !== null;
  return (
    <MapContainer
      center={hasPin ? [lat!, lng!] : DEFAULT_CENTER}
      zoom={hasPin ? 15 : DEFAULT_ZOOM}
      className="location-picker"
    >
      <TileLayer url={TILE_URL} attribution={TILE_ATTRIBUTION} />
      <ClickHandler onPick={onChange} />
      {hasPin && <Marker position={[lat!, lng!]} />}
    </MapContainer>
  );
}
