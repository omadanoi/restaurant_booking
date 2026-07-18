import { useRef, useState, type PointerEvent } from "react";

import type { DiningTable, Floor } from "../api/types";

interface FloorCanvasProps {
  floor: Floor;
  tables: DiningTable[];
  mode?: "view" | "edit";
  /** When set (availability mode), tables NOT in the set render dimmed and unclickable. */
  selectableIds?: Set<string> | null;
  selectedId?: string | null;
  onSelect?: (table: DiningTable) => void;
  /** Edit mode: fired when a drag ends, with the final position. */
  onMove?: (tableId: string, x: number, y: number) => void;
}

const SHAPE_SIZE = { rectangle: { w: 84, h: 52 }, square: { w: 60, h: 60 }, circle: { r: 34 } };

export function FloorCanvas({
  floor,
  tables,
  mode = "view",
  selectableIds = null,
  selectedId = null,
  onSelect,
  onMove,
}: FloorCanvasProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  // Positions being dragged right now (id -> x/y), rendered on top of props.
  const [dragPos, setDragPos] = useState<Record<string, { x: number; y: number }>>({});
  const dragState = useRef<{ id: string; offsetX: number; offsetY: number } | null>(null);

  function svgPoint(e: PointerEvent): { x: number; y: number } {
    const svg = svgRef.current!;
    const ctm = svg.getScreenCTM();
    if (!ctm) return { x: 0, y: 0 };
    const point = new DOMPoint(e.clientX, e.clientY).matrixTransform(ctm.inverse());
    return { x: point.x, y: point.y };
  }

  function handlePointerDown(e: PointerEvent, table: DiningTable) {
    if (mode !== "edit") return;
    const { x, y } = svgPoint(e);
    dragState.current = { id: table.id, offsetX: x - table.x, offsetY: y - table.y };
    (e.target as Element).setPointerCapture(e.pointerId);
  }

  function handlePointerMove(e: PointerEvent) {
    const drag = dragState.current;
    if (!drag) return;
    const { x, y } = svgPoint(e);
    const nx = Math.min(Math.max(x - drag.offsetX, 0), floor.width);
    const ny = Math.min(Math.max(y - drag.offsetY, 0), floor.height);
    setDragPos((p) => ({ ...p, [drag.id]: { x: nx, y: ny } }));
  }

  function handlePointerUp() {
    const drag = dragState.current;
    if (!drag) return;
    dragState.current = null;
    const pos = dragPos[drag.id];
    if (pos) onMove?.(drag.id, Math.round(pos.x), Math.round(pos.y));
  }

  return (
    <svg
      ref={svgRef}
      className="floor-canvas"
      viewBox={`0 0 ${floor.width} ${floor.height}`}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
    >
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
            onClick={() => !dimmed && onSelect?.(table)}
            onPointerDown={(e) => handlePointerDown(e, table)}
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
