/** One-time Leaflet configuration, imported by every map component.
 *
 * Bundlers break Leaflet's default marker icon (it resolves icon paths from
 * the stylesheet URL at runtime), so we point it at the Vite-bundled assets
 * explicitly. Tiles come from CARTO's dark basemap so the map reads as part
 * of the app's dark theme rather than a bright hole in the page.
 */
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import iconRetinaUrl from "leaflet/dist/images/marker-icon-2x.png";
import iconUrl from "leaflet/dist/images/marker-icon.png";
import shadowUrl from "leaflet/dist/images/marker-shadow.png";

L.Icon.Default.mergeOptions({ iconRetinaUrl, iconUrl, shadowUrl });

export const TILE_URL = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
export const TILE_ATTRIBUTION =
  '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>';
