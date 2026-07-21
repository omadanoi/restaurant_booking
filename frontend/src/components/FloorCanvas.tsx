import { useRef, useState, type PointerEvent } from "react";

import type { DiningTable, ElementType, Floor, FloorElement } from "../api/types";

export interface ElementGeom {
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
}

interface FloorCanvasProps {
  floor: Floor;
  tables: DiningTable[];
  /** Non-bookable layout features (walls, doors, windows…) drawn behind tables. */
  elements?: FloorElement[];
  mode?: "view" | "edit";
  /** When set (availability mode), tables NOT in the set render dimmed and unclickable. */
  selectableIds?: Set<string> | null;
  selectedId?: string | null;
  onSelect?: (table: DiningTable) => void;
  /** Edit mode: fired when a table drag ends, with the final position. */
  onMove?: (tableId: string, x: number, y: number) => void;
  /** Edit mode: the currently selected element (shows move/rotate/resize handles). */
  selectedElementId?: string | null;
  onSelectElement?: (element: FloorElement | null) => void;
  /** Edit mode: fired when an element drag/resize/rotate ends, with final geometry. */
  onElementChange?: (elementId: string, geom: ElementGeom) => void;
}

const SHAPE_SIZE = { rectangle: { w: 84, h: 52 }, square: { w: 60, h: 60 }, circle: { r: 34 } };
const MIN_ELEMENT_SIZE = 10;
const CORNERS: [number, number][] = [
  [-1, -1],
  [1, -1],
  [1, 1],
  [-1, 1],
];

type Interaction =
  | { kind: "table"; id: string; offsetX: number; offsetY: number }
  | { kind: "el-move"; id: string; offsetX: number; offsetY: number }
  | { kind: "el-rotate"; id: string; cx: number; cy: number }
  | {
      kind: "el-resize";
      id: string;
      sx: number;
      sy: number;
      rotation: number;
      fixedX: number;
      fixedY: number;
    };

/** Rotate a vector (x, y) by `deg` degrees about the origin. */
function rotate(x: number, y: number, deg: number): { x: number; y: number } {
  const r = (deg * Math.PI) / 180;
  const cos = Math.cos(r);
  const sin = Math.sin(r);
  return { x: x * cos - y * sin, y: x * sin + y * cos };
}

export function FloorCanvas({
  floor,
  tables,
  elements = [],
  mode = "view",
  selectableIds = null,
  selectedId = null,
  onSelect,
  onMove,
  selectedElementId = null,
  onSelectElement,
  onElementChange,
}: FloorCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  // Table positions being dragged right now (id -> x/y), rendered on top of props.
  const [dragPos, setDragPos] = useState<Record<string, { x: number; y: number }>>({});
  // Element geometry being dragged/resized/rotated right now, rendered on top of props.
  const [elDraft, setElDraft] = useState<Record<string, ElementGeom>>({});
  const interaction = useRef<Interaction | null>(null);

  function svgPoint(e: PointerEvent): { x: number; y: number } {
    const svg = svgRef.current!;
    const ctm = svg.getScreenCTM();
    if (!ctm) return { x: 0, y: 0 };
    const point = new DOMPoint(e.clientX, e.clientY).matrixTransform(ctm.inverse());
    return { x: point.x, y: point.y };
  }

  function geomOf(el: FloorElement): ElementGeom {
    return elDraft[el.id] ?? { x: el.x, y: el.y, width: el.width, height: el.height, rotation: el.rotation };
  }

  // -- tables -----------------------------------------------------------------

  function handleTableDown(e: PointerEvent, table: DiningTable) {
    if (mode !== "edit") return;
    const { x, y } = svgPoint(e);
    interaction.current = { kind: "table", id: table.id, offsetX: x - table.x, offsetY: y - table.y };
    (e.target as Element).setPointerCapture(e.pointerId);
  }

  // -- elements ---------------------------------------------------------------

  function handleElementDown(e: PointerEvent, el: FloorElement) {
    if (mode !== "edit") return;
    e.stopPropagation();
    onSelectElement?.(el);
    const { x, y } = svgPoint(e);
    const g = geomOf(el);
    interaction.current = { kind: "el-move", id: el.id, offsetX: x - g.x, offsetY: y - g.y };
    (e.target as Element).setPointerCapture(e.pointerId);
  }

  function handleRotateDown(e: PointerEvent, el: FloorElement) {
    e.stopPropagation();
    const g = geomOf(el);
    interaction.current = { kind: "el-rotate", id: el.id, cx: g.x, cy: g.y };
    (e.target as Element).setPointerCapture(e.pointerId);
  }

  function handleResizeDown(e: PointerEvent, el: FloorElement, sx: number, sy: number) {
    e.stopPropagation();
    const g = geomOf(el);
    // World position of the corner OPPOSITE the one being dragged — it stays put.
    const fixedLocal = { x: (-sx * g.width) / 2, y: (-sy * g.height) / 2 };
    const rotated = rotate(fixedLocal.x, fixedLocal.y, g.rotation);
    interaction.current = {
      kind: "el-resize",
      id: el.id,
      sx,
      sy,
      rotation: g.rotation,
      fixedX: g.x + rotated.x,
      fixedY: g.y + rotated.y,
    };
    (e.target as Element).setPointerCapture(e.pointerId);
  }

  // -- shared pointer move / up ----------------------------------------------

  function handlePointerMove(e: PointerEvent) {
    const act = interaction.current;
    if (!act) return;
    const { x, y } = svgPoint(e);

    if (act.kind === "table") {
      const nx = Math.min(Math.max(x - act.offsetX, 0), floor.width);
      const ny = Math.min(Math.max(y - act.offsetY, 0), floor.height);
      setDragPos((p) => ({ ...p, [act.id]: { x: nx, y: ny } }));
      return;
    }

    const base = elDraft[act.id] ?? propGeom(elements, act.id);
    if (!base) return;

    if (act.kind === "el-move") {
      const nx = Math.min(Math.max(x - act.offsetX, 0), floor.width);
      const ny = Math.min(Math.max(y - act.offsetY, 0), floor.height);
      setElDraft((d) => ({ ...d, [act.id]: { ...base, x: nx, y: ny } }));
    } else if (act.kind === "el-rotate") {
      const deg = (Math.atan2(y - act.cy, x - act.cx) * 180) / Math.PI + 90;
      setElDraft((d) => ({ ...d, [act.id]: { ...base, rotation: ((deg % 360) + 360) % 360 } }));
    } else {
      // Resize in the element's local (un-rotated) frame, keeping the opposite corner fixed.
      const vec = rotate(x - act.fixedX, y - act.fixedY, -act.rotation);
      const width = Math.max(MIN_ELEMENT_SIZE, Math.abs(vec.x));
      const height = Math.max(MIN_ELEMENT_SIZE, Math.abs(vec.y));
      const fixedLocalNew = { x: (-act.sx * width) / 2, y: (-act.sy * height) / 2 };
      const rotated = rotate(fixedLocalNew.x, fixedLocalNew.y, act.rotation);
      setElDraft((d) => ({
        ...d,
        [act.id]: { x: act.fixedX - rotated.x, y: act.fixedY - rotated.y, width, height, rotation: act.rotation },
      }));
    }
  }

  function handlePointerUp() {
    const act = interaction.current;
    if (!act) return;
    interaction.current = null;

    if (act.kind === "table") {
      const pos = dragPos[act.id];
      if (pos) onMove?.(act.id, Math.round(pos.x), Math.round(pos.y));
      return;
    }
    const g = elDraft[act.id];
    if (g) {
      onElementChange?.(act.id, {
        x: Math.round(g.x),
        y: Math.round(g.y),
        width: Math.round(g.width),
        height: Math.round(g.height),
        rotation: Math.round(g.rotation),
      });
    }
  }

  return (
    <svg
      ref={svgRef}
      className={`floor-canvas${mode === "edit" ? " editing" : ""}`}
      viewBox={`0 0 ${floor.width} ${floor.height}`}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onClick={() => mode === "edit" && onSelectElement?.(null)}
    >
      {/* Layout features first, so tables always sit on top of them. */}
      {elements.map((el) => {
        const g = geomOf(el);
        const selected = mode === "edit" && el.id === selectedElementId;
        return (
          <g
            key={el.id}
            className={`floor-el fe-${el.element_type}${selected ? " selected" : ""}`}
            transform={`translate(${g.x}, ${g.y}) rotate(${g.rotation})`}
            onPointerDown={(e) => handleElementDown(e, el)}
            onClick={(e) => e.stopPropagation()}
          >
            <ElementShape type={el.element_type} width={g.width} height={g.height} label={el.label} />
            {selected && <ElementHandles el={el} geom={g} onRotateDown={handleRotateDown} onResizeDown={handleResizeDown} />}
          </g>
        );
      })}

      {tables.map((table) => {
        const pos = dragPos[table.id] ?? { x: table.x, y: table.y };
        const dimmed = selectableIds !== null && !selectableIds.has(table.id);
        const classes = [
          "floor-table",
          `st-${table.status}`,
          dimmed ? "dimmed" : "",
          table.id === selectedId ? "selected" : "",
        ]
          .filter(Boolean)
          .join(" ");

        return (
          <g
            key={table.id}
            className={classes}
            transform={`translate(${pos.x}, ${pos.y}) rotate(${table.rotation})`}
            onClick={(e) => {
              e.stopPropagation();
              if (!dimmed) onSelect?.(table);
            }}
            onPointerDown={(e) => handleTableDown(e, table)}
          >
            {table.shape === "circle" ? (
              <circle className="shape" r={SHAPE_SIZE.circle.r} />
            ) : (
              <rect
                className="shape"
                x={-size(table).w / 2}
                y={-size(table).h / 2}
                width={size(table).w}
                height={size(table).h}
                rx={8}
              />
            )}
            <text y={-6}>{table.table_number}</text>
            <text y={10} className="cap">
              {table.capacity} seats{table.is_accessible ? " ♿" : ""}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

function propGeom(elements: FloorElement[], id: string): ElementGeom | null {
  const el = elements.find((e) => e.id === id);
  return el ? { x: el.x, y: el.y, width: el.width, height: el.height, rotation: el.rotation } : null;
}

function ElementShape({
  type,
  width,
  height,
  label,
}: {
  type: ElementType;
  width: number;
  height: number;
  label: string | null;
}) {
  if (type === "plant") {
    return <circle className="shape" r={Math.min(width, height) / 2} />;
  }
  const showLabel = label && type !== "wall" && type !== "window" && type !== "door";
  return (
    <>
      {type !== "label" && (
        <rect
          className="shape"
          x={-width / 2}
          y={-height / 2}
          width={width}
          height={height}
          rx={type === "wall" ? 2 : 5}
        />
      )}
      {(showLabel || type === "label") && (
        <text className="fe-label">{label ?? "Label"}</text>
      )}
    </>
  );
}

function ElementHandles({
  el,
  geom,
  onRotateDown,
  onResizeDown,
}: {
  el: FloorElement;
  geom: ElementGeom;
  onRotateDown: (e: PointerEvent, el: FloorElement) => void;
  onResizeDown: (e: PointerEvent, el: FloorElement, sx: number, sy: number) => void;
}) {
  const hw = geom.width / 2;
  const hh = geom.height / 2;
  return (
    <g className="fe-handles">
      <line className="fe-rot-arm" x1={0} y1={-hh} x2={0} y2={-hh - 26} />
      <circle
        className="fe-rot-handle"
        cx={0}
        cy={-hh - 26}
        r={7}
        onPointerDown={(e) => onRotateDown(e, el)}
      />
      {CORNERS.map(([sx, sy]) => (
        <rect
          key={`${sx},${sy}`}
          className="fe-resize-handle"
          x={sx * hw - 6}
          y={sy * hh - 6}
          width={12}
          height={12}
          onPointerDown={(e) => onResizeDown(e, el, sx, sy)}
        />
      ))}
    </g>
  );
}

function size(table: DiningTable): { w: number; h: number } {
  return table.shape === "square" ? SHAPE_SIZE.square : SHAPE_SIZE.rectangle;
}

export function FloorLegend() {
  const entries: [string, string][] = [
    ["available", "var(--green)"],
    ["reserved", "var(--amber)"],
    ["occupied", "var(--red)"],
    ["cleaning", "var(--blue)"],
    ["out of service", "var(--text-dim)"],
  ];
  return (
    <div className="legend">
      {entries.map(([label, color]) => (
        <span key={label} className="item">
          <span className="dot" style={{ background: color }} />
          {label}
        </span>
      ))}
    </div>
  );
}
