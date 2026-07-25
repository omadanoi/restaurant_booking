import { useEffect, useMemo, useState } from "react";

import { ApiError } from "../api/client";
import {
  createElement,
  createFloor,
  createTable,
  deactivateTable,
  deleteElement,
  getOpeningHours,
  listElements,
  listFloors,
  listTables,
  setOpeningHours,
  updateElement,
  updateTable,
} from "../api/endpoints";
import type {
  DiningTable,
  ElementType,
  FloorElement,
  OpeningHours,
  TableShape,
} from "../api/types";
import { FloorCanvas, type ElementGeom } from "../components/FloorCanvas";
import { RestaurantSettingsPanel } from "../components/RestaurantSettingsPanel";
import { useApi } from "../hooks/useApi";
import { useMyRestaurants } from "../hooks/useMyRestaurants";

const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

// Palette of layout features a manager can drop onto the floor. Each has a
// sensible default size (and caption, for the labelled ones).
const ELEMENT_PALETTE: {
  type: ElementType;
  label: string;
  width: number;
  height: number;
  caption?: string;
}[] = [
  { type: "wall", label: "Wall", width: 200, height: 12 },
  { type: "window", label: "Window", width: 100, height: 10 },
  { type: "door", label: "Door", width: 50, height: 12 },
  { type: "entrance", label: "Entrance", width: 80, height: 16, caption: "Entrance" },
  { type: "restroom", label: "Restrooms", width: 110, height: 80, caption: "Restrooms" },
  { type: "bar", label: "Bar", width: 200, height: 50, caption: "Bar" },
  { type: "kitchen", label: "Kitchen", width: 140, height: 100, caption: "Kitchen" },
  { type: "plant", label: "Plant", width: 40, height: 40 },
  { type: "label", label: "Text", width: 100, height: 30, caption: "Label" },
];

// Element types that carry an editable caption.
const LABELLED_TYPES: ElementType[] = ["entrance", "restroom", "bar", "kitchen", "label"];

export function FloorEditorPage() {
  const { restaurants, selected, selectedId, setSelectedId, loading } = useMyRestaurants();
  const [tab, setTab] = useState<"layout" | "hours" | "settings">("layout");

  if (loading) return <p className="muted">Loading…</p>;
  if (restaurants.length === 0) {
    return <p className="muted">You are not assigned to any restaurant.</p>;
  }

  return (
    <>
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1>Manage{selected ? ` — ${selected.name}` : ""}</h1>
        <div className="row">
          {restaurants.length > 1 && (
            <select value={selectedId ?? ""} onChange={(e) => setSelectedId(e.target.value)}>
              {restaurants.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          )}
          <button className={tab === "layout" ? "primary" : ""} onClick={() => setTab("layout")}>
            Floor layout
          </button>
          <button className={tab === "hours" ? "primary" : ""} onClick={() => setTab("hours")}>
            Opening hours
          </button>
          <button
            className={tab === "settings" ? "primary" : ""}
            onClick={() => setTab("settings")}
          >
            Settings
          </button>
        </div>
      </div>
      {selectedId && tab === "layout" && <LayoutEditor restaurantId={selectedId} />}
      {selectedId && tab === "hours" && <HoursEditor restaurantId={selectedId} />}
      {selectedId && tab === "settings" && <RestaurantSettingsPanel restaurantId={selectedId} />}
    </>
  );
}

// -- layout editor ------------------------------------------------------------

function LayoutEditor({ restaurantId }: { restaurantId: string }) {
  const floorsApi = useApi(() => listFloors(restaurantId), [restaurantId]);
  const tablesApi = useApi(() => listTables(restaurantId), [restaurantId]);
  const elementsApi = useApi(() => listElements(restaurantId), [restaurantId]);

  const [activeFloorId, setActiveFloorId] = useState<string | null>(null);
  const [selectedTable, setSelectedTable] = useState<DiningTable | null>(null);
  const [selectedElementId, setSelectedElementId] = useState<string | null>(null);
  const [labelDraft, setLabelDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [newTable, setNewTable] = useState({ number: "", capacity: 4, shape: "rectangle" as TableShape });
  const [newFloorName, setNewFloorName] = useState("");

  const floors = floorsApi.data ?? [];
  const floor = floors.find((f) => f.id === activeFloorId) ?? floors[0] ?? null;
  const floorTables = useMemo(
    () => (tablesApi.data ?? []).filter((t) => t.floor_id === floor?.id),
    [tablesApi.data, floor],
  );
  const floorElements = useMemo(
    () => (elementsApi.data ?? []).filter((e) => e.floor_id === floor?.id),
    [elementsApi.data, floor],
  );
  // Always read the selected element from the live list so its geometry/label
  // stay correct after a drag or reload.
  const selectedElement = floorElements.find((e) => e.id === selectedElementId) ?? null;

  // Keep the label field in sync when the selection changes.
  useEffect(() => {
    setLabelDraft(selectedElement?.label ?? "");
  }, [selectedElementId, selectedElement?.label]);

  function flash(text: string) {
    setSaved(text);
    window.setTimeout(() => setSaved(null), 2500);
  }

  async function run(action: () => Promise<unknown>, okMessage: string) {
    setError(null);
    try {
      await action();
      await Promise.all([tablesApi.reload(), elementsApi.reload()]);
      flash(okMessage);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Operation failed.");
    }
  }

  async function handleMove(tableId: string, x: number, y: number) {
    await run(() => updateTable(restaurantId, tableId, { x, y }), "Position saved");
  }

  async function rotate(table: DiningTable) {
    const rotation = (table.rotation + 15) % 360;
    await run(() => updateTable(restaurantId, table.id, { rotation }), `Rotated to ${rotation}°`);
    setSelectedTable({ ...table, rotation });
  }

  async function changeCapacity(table: DiningTable, capacity: number) {
    if (capacity < 1) return;
    await run(() => updateTable(restaurantId, table.id, { capacity }), "Capacity saved");
    setSelectedTable({ ...table, capacity });
  }

  async function addTable() {
    if (!floor || !newTable.number) return;
    await run(
      () =>
        createTable(restaurantId, {
          floor_id: floor.id,
          table_number: newTable.number,
          capacity: newTable.capacity,
          shape: newTable.shape,
          x: floor.width / 2,
          y: floor.height / 2,
        }),
      `Table ${newTable.number} added`,
    );
    setNewTable({ number: "", capacity: 4, shape: "rectangle" });
  }

  async function removeTable(table: DiningTable) {
    await run(() => deactivateTable(restaurantId, table.id), `Table ${table.table_number} removed`);
    setSelectedTable(null);
  }

  // -- layout elements (walls, doors, windows…) -------------------------------

  async function addElement(preset: (typeof ELEMENT_PALETTE)[number]) {
    if (!floor) return;
    await run(
      () =>
        createElement(restaurantId, {
          floor_id: floor.id,
          element_type: preset.type,
          x: Math.round(floor.width / 2),
          y: Math.round(floor.height / 2),
          width: preset.width,
          height: preset.height,
          label: preset.caption ?? null,
        }),
      `${preset.label} added`,
    );
  }

  async function handleElementChange(elementId: string, geom: ElementGeom) {
    await run(() => updateElement(restaurantId, elementId, geom), "Layout saved");
  }

  async function rotateElement(element: FloorElement) {
    const rotation = Math.round((element.rotation + 15) % 360);
    await run(() => updateElement(restaurantId, element.id, { rotation }), `Rotated to ${rotation}°`);
  }

  async function commitLabel(element: FloorElement) {
    const label = labelDraft.trim() || null;
    if (label === (element.label ?? null)) return;
    await run(() => updateElement(restaurantId, element.id, { label }), "Label saved");
  }

  async function removeElement(element: FloorElement) {
    await run(() => deleteElement(restaurantId, element.id), "Element removed");
    setSelectedElementId(null);
  }

  async function addFloor() {
    if (!newFloorName) return;
    setError(null);
    try {
      await createFloor(restaurantId, { name: newFloorName, level: floors.length });
      setNewFloorName("");
      await floorsApi.reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not add floor.");
    }
  }

  return (
    <>
      {error && <div className="error">{error}</div>}
      {saved && <div className="toast">{saved}</div>}

      <div className="row" style={{ margin: "0.75rem 0" }}>
        {floors.map((f) => (
          <button
            key={f.id}
            className={f.id === floor?.id ? "primary" : ""}
            onClick={() => {
              setActiveFloorId(f.id);
              setSelectedTable(null);
            }}
          >
            {f.name}
          </button>
        ))}
        <input
          placeholder="New floor name…"
          value={newFloorName}
          onChange={(e) => setNewFloorName(e.target.value)}
          style={{ width: "10rem" }}
        />
        <button onClick={addFloor}>+ Add floor</button>
      </div>

      <p className="muted">
        Drag tables or layout features to move them. Click a table to edit it; select a feature to
        resize (drag a corner), rotate (drag the top handle) or delete it.
      </p>

      {floor && (
        <div className="floor-wrap">
          <FloorCanvas
            floor={floor}
            tables={floorTables}
            elements={floorElements}
            mode="edit"
            selectedId={selectedTable?.id ?? null}
            onSelect={(t) => {
              setSelectedElementId(null);
              setSelectedTable(t.id === selectedTable?.id ? null : t);
            }}
            onMove={handleMove}
            selectedElementId={selectedElementId}
            onSelectElement={(el) => {
              setSelectedTable(null);
              setSelectedElementId(el?.id ?? null);
            }}
            onElementChange={handleElementChange}
          />
        </div>
      )}

      <div className="row" style={{ marginTop: "1rem", alignItems: "stretch" }}>
        <div className="card" style={{ flex: 1, minWidth: "300px" }}>
          <h2>Add table</h2>
          <div className="row">
            <label className="field">
              Number
              <input
                value={newTable.number}
                onChange={(e) => setNewTable((t) => ({ ...t, number: e.target.value }))}
                style={{ width: "5.5rem" }}
              />
            </label>
            <label className="field">
              Capacity
              <input
                type="number"
                min={1}
                max={50}
                value={newTable.capacity}
                onChange={(e) => setNewTable((t) => ({ ...t, capacity: Number(e.target.value) }))}
                style={{ width: "5rem" }}
              />
            </label>
            <label className="field">
              Shape
              <select
                value={newTable.shape}
                onChange={(e) => setNewTable((t) => ({ ...t, shape: e.target.value as TableShape }))}
              >
                <option value="rectangle">Rectangle</option>
                <option value="square">Square</option>
                <option value="circle">Circle</option>
              </select>
            </label>
            <button className="primary" onClick={addTable} style={{ alignSelf: "end" }}>
              Add
            </button>
          </div>
        </div>

        {selectedTable && (
          <div className="card" style={{ flex: 1, minWidth: "300px" }}>
            <h2>Table {selectedTable.table_number}</h2>
            <div className="row">
              <button onClick={() => rotate(selectedTable)}>Rotate +15°</button>
              <label className="field">
                Capacity
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={selectedTable.capacity}
                  onChange={(e) => changeCapacity(selectedTable, Number(e.target.value))}
                  style={{ width: "5rem" }}
                />
              </label>
              <button className="danger" onClick={() => removeTable(selectedTable)}>
                Remove table
              </button>
            </div>
          </div>
        )}
      </div>

      <div className="row" style={{ marginTop: "1rem", alignItems: "stretch" }}>
        <div className="card" style={{ flex: 1, minWidth: "300px" }}>
          <h2>Add layout feature</h2>
          <p className="muted" style={{ marginTop: 0 }}>
            Walls, windows and fixtures help customers picture the room — a window seat, a table by
            the bar. They can't be booked.
          </p>
          <div className="row" style={{ flexWrap: "wrap" }}>
            {ELEMENT_PALETTE.map((preset) => (
              <button key={preset.type} onClick={() => addElement(preset)} disabled={!floor}>
                + {preset.label}
              </button>
            ))}
          </div>
        </div>

        {selectedElement && (
          <div className="card" style={{ flex: 1, minWidth: "300px" }}>
            <h2 style={{ textTransform: "capitalize" }}>{selectedElement.element_type}</h2>
            <div className="row">
              <button onClick={() => rotateElement(selectedElement)}>Rotate +15°</button>
              {LABELLED_TYPES.includes(selectedElement.element_type) && (
                <label className="field" style={{ flex: 1, minWidth: "8rem" }}>
                  Label
                  <input
                    value={labelDraft}
                    onChange={(e) => setLabelDraft(e.target.value)}
                    onBlur={() => commitLabel(selectedElement)}
                    onKeyDown={(e) => e.key === "Enter" && commitLabel(selectedElement)}
                  />
                </label>
              )}
              <button className="danger" onClick={() => removeElement(selectedElement)}>
                Remove
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}

// -- opening hours editor -----------------------------------------------------

function HoursEditor({ restaurantId }: { restaurantId: string }) {
  const { data, loading, error, reload } = useApi(() => getOpeningHours(restaurantId), [restaurantId]);
  const [draft, setDraft] = useState<OpeningHours[] | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const hours: OpeningHours[] =
    draft ??
    DAYS.map((_, day) => {
      const existing = data?.find((h) => h.day_of_week === day);
      return (
        existing ?? { day_of_week: day, opens_at: "11:00:00", closes_at: "22:00:00", is_closed: false }
      );
    });

  function update(day: number, patch: Partial<OpeningHours>) {
    setDraft(hours.map((h) => (h.day_of_week === day ? { ...h, ...patch } : h)));
  }

  async function save() {
    setSaveError(null);
    setSaved(false);
    try {
      await setOpeningHours(restaurantId, hours);
      setDraft(null);
      setSaved(true);
      await reload();
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.detail : "Could not save hours.");
    }
  }

  if (loading) return <p className="muted">Loading…</p>;

  return (
    <div className="card" style={{ marginTop: "1rem", maxWidth: "560px" }}>
      {error && <div className="error">{error}</div>}
      {saveError && <div className="error">{saveError}</div>}
      {saved && <div className="success">Opening hours saved.</div>}
      <table className="data">
        <thead>
          <tr>
            <th>Day</th>
            <th>Open</th>
            <th>Close</th>
            <th>Closed</th>
          </tr>
        </thead>
        <tbody>
          {hours.map((h) => (
            <tr key={h.day_of_week}>
              <td>{DAYS[h.day_of_week]}</td>
              <td>
                <input
                  type="time"
                  disabled={h.is_closed}
                  value={h.opens_at?.slice(0, 5) ?? ""}
                  onChange={(e) => update(h.day_of_week, { opens_at: `${e.target.value}:00` })}
                />
              </td>
              <td>
                <input
                  type="time"
                  disabled={h.is_closed}
                  value={h.closes_at?.slice(0, 5) ?? ""}
                  onChange={(e) => update(h.day_of_week, { closes_at: `${e.target.value}:00` })}
                />
              </td>
              <td>
                <input
                  type="checkbox"
                  checked={h.is_closed}
                  onChange={(e) => update(h.day_of_week, { is_closed: e.target.checked })}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <button className="primary" style={{ marginTop: "1rem" }} onClick={save}>
        Save hours
      </button>
    </div>
  );
}
