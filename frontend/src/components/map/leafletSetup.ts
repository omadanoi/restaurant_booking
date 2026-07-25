/** One-time Leaflet configuration, imported by every map component.
 *
 * Bundlers break Leaflet's default marker icon (its `_getIconUrl` computes
 * paths from the stylesheet location at runtime, overriding any URLs set via
 * options — it must be deleted BEFORE mergeOptions takes effect). We point it
 * at the Vite-bundled assets explicitly. Tiles come from CARTO's light-grey
 * "Positron" basemap: streets and labels stay readable, unlike the near-black
 * dark tiles, and the surrounding card frames it against the dark UI.
 */
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({ iconRetinaUrl, iconUrl, shadowUrl });

export const TILE_URL = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
export const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';
