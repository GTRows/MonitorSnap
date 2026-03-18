import { useRef, useState, useCallback, useEffect, useMemo } from 'react';
import type { Monitor } from '@/types';

interface MonitorCanvasProps {
  monitors: Monitor[];
  editable?: boolean;
  onMonitorsChange?: (monitors: Monitor[]) => void;
  onLayoutValidChange?: (valid: boolean) => void;
  selectedMonitorId?: string | null;
  onSelectMonitor?: (id: string | null) => void;
  className?: string;
}

interface SnapGuide {
  type: 'vertical' | 'horizontal';
  monitorCoord: number;
}

// Returns the on-screen footprint of a monitor.
// Windows swaps width/height in display coordinates for 90/270 rotations.
function getEffectiveDims(m: Monitor): { w: number; h: number } {
  return m.rotation === 90 || m.rotation === 270
    ? { w: m.height, h: m.width }
    : { w: m.width, h: m.height };
}

const CANVAS_PADDING = 48;
const SNAP_THRESHOLD_PX = 14;
// Tolerance (monitor-space pixels) for "touching" check to account for rounding
const TOUCH_TOLERANCE = 2;

// ── Layout validation ────────────────────────────────────────────────────────

function monitorsTouch(a: Monitor, b: Monitor): boolean {
  const { w: aw, h: ah } = getEffectiveDims(a);
  const { w: bw, h: bh } = getEffectiveDims(b);

  // Same position (duplicate/clone) — treat as connected
  if (a.x === b.x && a.y === b.y && aw === bw && ah === bh) return true;

  const rightToLeft = Math.abs(a.x + aw - b.x) <= TOUCH_TOLERANCE;
  const leftToRight = Math.abs(b.x + bw - a.x) <= TOUCH_TOLERANCE;
  const yOverlap = a.y < b.y + bh && b.y < a.y + ah;

  const bottomToTop = Math.abs(a.y + ah - b.y) <= TOUCH_TOLERANCE;
  const topToBottom = Math.abs(b.y + bh - a.y) <= TOUCH_TOLERANCE;
  const xOverlap = a.x < b.x + bw && b.x < a.x + aw;

  return ((rightToLeft || leftToRight) && yOverlap) ||
         ((bottomToTop || topToBottom) && xOverlap);
}

export function monitorsAreConnected(monitors: Monitor[]): boolean {
  if (monitors.length <= 1) return true;

  const connected = new Set<string>([monitors[0].id]);
  let changed = true;
  while (changed) {
    changed = false;
    for (const m of monitors) {
      if (connected.has(m.id)) continue;
      for (const other of monitors) {
        if (!connected.has(other.id)) continue;
        if (monitorsTouch(m, other)) {
          connected.add(m.id);
          changed = true;
          break;
        }
      }
    }
  }
  return connected.size === monitors.length;
}

// ── Canvas transform ─────────────────────────────────────────────────────────

function getCanvasTransform(
  monitors: Monitor[],
  containerWidth: number,
  containerHeight: number
): { scale: number; offsetX: number; offsetY: number } {
  if (monitors.length === 0) return { scale: 1, offsetX: 0, offsetY: 0 };

  const minX = Math.min(...monitors.map((m) => m.x));
  const minY = Math.min(...monitors.map((m) => m.y));
  const maxX = Math.max(...monitors.map((m) => m.x + getEffectiveDims(m).w));
  const maxY = Math.max(...monitors.map((m) => m.y + getEffectiveDims(m).h));

  const totalW = Math.max(maxX - minX, 1);
  const totalH = Math.max(maxY - minY, 1);

  const availW = containerWidth - CANVAS_PADDING * 2;
  const availH = containerHeight - CANVAS_PADDING * 2;

  const scale = Math.min(availW / totalW, availH / totalH, 0.15);
  const scaledW = totalW * scale;
  const scaledH = totalH * scale;

  return {
    scale,
    offsetX: (containerWidth - scaledW) / 2 - minX * scale,
    offsetY: (containerHeight - scaledH) / 2 - minY * scale,
  };
}

// ── Snap ─────────────────────────────────────────────────────────────────────

function computeSnap(
  draggedId: string,
  dragGroupIds: Set<string>,
  rawX: number,
  rawY: number,
  monitors: Monitor[],
  scale: number
): { x: number; y: number; guides: SnapGuide[] } {
  const dragged = monitors.find((m) => m.id === draggedId);
  if (!dragged) return { x: rawX, y: rawY, guides: [] };

  const { w: dw, h: dh } = getEffectiveDims(dragged);
  const threshold = SNAP_THRESHOLD_PX / scale;

  let bestX = rawX;
  let bestXDist = Infinity;
  let bestY = rawY;
  let bestYDist = Infinity;
  const guides: SnapGuide[] = [];

  for (const other of monitors) {
    if (dragGroupIds.has(other.id)) continue;
    const { w: ow, h: oh } = getEffectiveDims(other);

    const ocx = other.x + ow / 2;
    const ocy = other.y + oh / 2;

    const xCandidates: Array<[number, number]> = [
      // Edge-to-edge
      [other.x + ow, other.x + ow],
      [other.x - dw, other.x],
      [other.x, other.x],
      [other.x + ow - dw, other.x + ow],
      // Center axis of other aligns with left / center / right of dragged
      [ocx, ocx],
      [ocx - dw / 2, ocx],
      [ocx - dw, ocx],
    ];
    for (const [snapTo, guideLine] of xCandidates) {
      const dist = Math.abs(snapTo - rawX);
      if (dist < threshold && dist < bestXDist) {
        bestX = snapTo;
        bestXDist = dist;
        guides.push({ type: 'vertical', monitorCoord: guideLine });
      }
    }

    const yCandidates: Array<[number, number]> = [
      // Edge-to-edge
      [other.y + oh, other.y + oh],
      [other.y - dh, other.y],
      [other.y, other.y],
      [other.y + oh - dh, other.y + oh],
      // Center axis of other aligns with top / center / bottom of dragged
      [ocy, ocy],
      [ocy - dh / 2, ocy],
      [ocy - dh, ocy],
    ];
    for (const [snapTo, guideLine] of yCandidates) {
      const dist = Math.abs(snapTo - rawY);
      if (dist < threshold && dist < bestYDist) {
        bestY = snapTo;
        bestYDist = dist;
        guides.push({ type: 'horizontal', monitorCoord: guideLine });
      }
    }
  }

  const seen = new Set<string>();
  return {
    x: bestX,
    y: bestY,
    guides: guides.filter((g) => {
      const key = `${g.type}:${g.monitorCoord}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    }),
  };
}

// ── Drag bounds: keep dragged monitor close to the rest of the layout ─────────

function computeDragBounds(
  draggedId: string,
  monitors: Monitor[]
): { minX: number; maxX: number; minY: number; maxY: number } {
  const others = monitors.filter((m) => m.id !== draggedId);
  if (others.length === 0) return { minX: -50000, maxX: 50000, minY: -50000, maxY: 50000 };

  const dragged = monitors.find((m) => m.id === draggedId)!;
  const { w: dw, h: dh } = getEffectiveDims(dragged);

  const oMinX = Math.min(...others.map((m) => m.x));
  const oMinY = Math.min(...others.map((m) => m.y));
  const oMaxX = Math.max(...others.map((m) => m.x + getEffectiveDims(m).w));
  const oMaxY = Math.max(...others.map((m) => m.y + getEffectiveDims(m).h));

  const layoutW = oMaxX - oMinX;
  const layoutH = oMaxY - oMinY;
  const marginX = layoutW + dw;
  const marginY = layoutH + dh;

  return {
    minX: oMinX - marginX,
    maxX: oMaxX + marginX,
    minY: oMinY - marginY,
    maxY: oMaxY + marginY,
  };
}

// ── Overlap check (skips same-position duplicates) ────────────────────────────

function hasOverlap(monitors: Monitor[], draggedId: string): boolean {
  for (let i = 0; i < monitors.length; i++) {
    for (let j = i + 1; j < monitors.length; j++) {
      const a = monitors[i];
      const b = monitors[j];
      if (a.id !== draggedId && b.id !== draggedId) continue;
      const { w: aw, h: ah } = getEffectiveDims(a);
      const { w: bw, h: bh } = getEffectiveDims(b);
      // Same position = intentional duplicate, not a problem
      if (a.x === b.x && a.y === b.y && aw === bw && ah === bh) continue;
      if (
        a.x < b.x + bw &&
        a.x + aw > b.x &&
        a.y < b.y + bh &&
        a.y + ah > b.y
      ) return true;
    }
  }
  return false;
}

// ── Position key ─────────────────────────────────────────────────────────────

function positionKey(m: Monitor): string {
  const { w, h } = getEffectiveDims(m);
  return `${m.x}:${m.y}:${w}:${h}`;
}

// ── MonitorBox ────────────────────────────────────────────────────────────────

function formatResLabel(m: Monitor): string {
  const { w, h } = getEffectiveDims(m);
  if (w === 3840 && h === 2160) return '4K UHD';
  if (w === 2160 && h === 3840) return '4K Portrait';
  if (w === 2560 && h === 1440) return 'QHD';
  if (w === 1440 && h === 2560) return 'QHD Portrait';
  if (w === 1920 && h === 1080) return 'FHD';
  if (w === 1080 && h === 1920) return 'FHD Portrait';
  return `${w}\u00d7${h}`;
}

function MonitorBox({
  monitor, groupMonitors, index, scale, offsetX, offsetY,
  isSelected, isHovered, isDragged, editable, overlapping,
  onMouseDown, onMouseEnter, onMouseLeave,
}: {
  monitor: Monitor;
  groupMonitors: Monitor[];
  index: number;
  scale: number; offsetX: number; offsetY: number;
  isSelected: boolean; isHovered: boolean; isDragged: boolean;
  editable: boolean; overlapping: boolean;
  onMouseDown: (e: React.MouseEvent) => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
}) {
  const { w, h } = getEffectiveDims(monitor);
  const isPortrait = monitor.rotation === 90 || monitor.rotation === 270;
  const isDuplicate = groupMonitors.length > 1;

  const screenX = monitor.x * scale + offsetX;
  const screenY = monitor.y * scale + offsetY;
  const screenW = w * scale;
  const screenH = h * scale;

  let borderCls = 'border-border-default';
  let bgCls = 'bg-[var(--monitor-bg)]';
  if (overlapping) {
    borderCls = 'border-orange-400';
    bgCls = 'bg-orange-500/10';
  } else if (isSelected) {
    borderCls = 'border-accent ring-1 ring-accent/30';
    bgCls = 'bg-accent/15';
  } else if (isDuplicate) {
    borderCls = 'border-accent/60';
    bgCls = 'bg-accent/8';
  } else if (monitor.isPrimary) {
    borderCls = 'border-accent';
    bgCls = 'bg-accent/10';
  }

  return (
    <div
      onMouseDown={onMouseDown}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      className={[
        'absolute flex flex-col items-center justify-center',
        'rounded-fluent border-2 select-none overflow-hidden',
        'transition-shadow duration-150',
        borderCls, bgCls,
        (isHovered || isDragged) ? 'shadow-fluent-lg' : '',
        isDragged ? 'z-50 opacity-90' : 'z-10',
        editable ? 'cursor-grab active:cursor-grabbing' : 'cursor-pointer',
      ].join(' ')}
      style={{
        left: screenX,
        top: screenY,
        width: screenW,
        height: screenH,
        // Card-stack shadow for duplicates
        ...(isDuplicate ? {
          boxShadow: '3px 3px 0 0 rgba(96,205,255,0.25), 6px 6px 0 0 rgba(96,205,255,0.12)',
        } : {}),
      }}
    >
      {/* Monitor index badge */}
      <div
        className="absolute top-1 left-1 w-4 h-4 rounded-full bg-accent/80 flex items-center justify-center pointer-events-none"
        style={{ fontSize: 9, fontWeight: 700, color: '#000', lineHeight: 1 }}
      >
        {index + 1}
      </div>

      {/* Duplicate count badge */}
      {isDuplicate && (
        <div
          className="absolute top-1 right-1 px-1 rounded bg-accent/20 text-accent pointer-events-none leading-tight"
          style={{ fontSize: 8, fontWeight: 700 }}
        >
          ×{groupMonitors.length}
        </div>
      )}

      <div className="flex flex-col items-center justify-center gap-0.5 px-1.5 w-full overflow-hidden">
        {isDuplicate ? (
          <>
            <span
              className="font-bold text-accent/70 uppercase tracking-wider"
              style={{ fontSize: Math.max(7, Math.min(9, screenH * 0.08)) }}
            >
              Duplicate
            </span>
            {groupMonitors.map((gm) => (
              <span
                key={gm.id}
                className="text-text-primary text-center leading-tight truncate w-full text-center"
                style={{ fontSize: Math.max(8, Math.min(11, screenH * 0.1)) }}
              >
                {gm.name}
              </span>
            ))}
            <span
              className="text-text-secondary text-center"
              style={{ fontSize: Math.max(8, Math.min(10, screenH * 0.09)) }}
            >
              {formatResLabel(monitor)}
            </span>
            <span
              className="text-text-tertiary text-center"
              style={{ fontSize: Math.max(8, Math.min(10, screenH * 0.09)) }}
            >
              {monitor.refreshRate}Hz
            </span>
          </>
        ) : (
          <>
            {isPortrait && (
              <span className="text-[9px] font-bold text-accent/80 uppercase tracking-widest">
                {monitor.rotation}deg
              </span>
            )}
            <span
              className="font-medium text-text-primary text-center leading-tight truncate w-full text-center"
              style={{ fontSize: Math.max(9, Math.min(13, screenH * 0.13)) }}
            >
              {monitor.name}
            </span>
            <span
              className="text-text-secondary text-center"
              style={{ fontSize: Math.max(8, Math.min(11, screenH * 0.1)) }}
            >
              {formatResLabel(monitor)}
            </span>
            <span
              className="text-text-tertiary text-center"
              style={{ fontSize: Math.max(8, Math.min(11, screenH * 0.09)) }}
            >
              {monitor.refreshRate}Hz
            </span>
            {monitor.isPrimary && (
              <span
                className="font-semibold text-accent uppercase tracking-wider"
                style={{ fontSize: Math.max(7, Math.min(10, screenH * 0.08)) }}
              >
                Primary
              </span>
            )}
            {overlapping && (
              <span
                className="font-semibold text-orange-400 uppercase tracking-wider"
                style={{ fontSize: Math.max(7, Math.min(10, screenH * 0.08)) }}
              >
                Overlap
              </span>
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ── MonitorCanvas ─────────────────────────────────────────────────────────────

export function MonitorCanvas({
  monitors,
  editable = false,
  onMonitorsChange,
  onLayoutValidChange,
  selectedMonitorId,
  onSelectMonitor,
  className = '',
}: MonitorCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerSize, setContainerSize] = useState({ width: 600, height: 350 });
  const [dragging, setDragging] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [snapGuides, setSnapGuides] = useState<SnapGuide[]>([]);
  // IDs of monitors that move together during the current drag (frozen at drag start)
  const dragGroupIdsRef = useRef<Set<string>>(new Set());

  // Group monitors by exact position — duplicates (clone/mirror) share a box
  const groups = useMemo(() => {
    const map = new Map<string, Monitor[]>();
    for (const m of monitors) {
      const key = positionKey(m);
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(m);
    }
    return map;
  }, [monitors]);

  // Map from monitor ID -> position key (for fast lookup during drag)
  const posKeyOf = useMemo(() => {
    const m = new Map<string, string>();
    for (const [key, grp] of groups) for (const mon of grp) m.set(mon.id, key);
    return m;
  }, [groups]);

  // Frozen snapshot of the canvas transform at drag-start.
  const frozenTransformRef = useRef<{
    scale: number;
    offsetX: number;
    offsetY: number;
    dragOffsetX: number;
    dragOffsetY: number;
  } | null>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) setContainerSize({ width: entry.contentRect.width, height: entry.contentRect.height });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const { scale, offsetX, offsetY } = getCanvasTransform(monitors, containerSize.width, containerSize.height);

  useEffect(() => {
    onLayoutValidChange?.(monitorsAreConnected(monitors));
  }, [monitors, onLayoutValidChange]);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent, monitorId: string) => {
      onSelectMonitor?.(monitorId);
      if (!editable) return;
      e.preventDefault();
      e.stopPropagation();

      const monitor = monitors.find((m) => m.id === monitorId);
      if (!monitor) return;

      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;

      const screenX = monitor.x * scale + offsetX;
      const screenY = monitor.y * scale + offsetY;

      frozenTransformRef.current = {
        scale,
        offsetX,
        offsetY,
        dragOffsetX: e.clientX - rect.left - screenX,
        dragOffsetY: e.clientY - rect.top - screenY,
      };

      // Freeze the group membership so position-key changes during drag don't break filtering
      const groupKey = posKeyOf.get(monitorId);
      const groupMembers = groupKey ? (groups.get(groupKey) ?? []) : [];
      dragGroupIdsRef.current = new Set(groupMembers.length ? groupMembers.map((m) => m.id) : [monitorId]);

      setDragging(monitorId);
    },
    [editable, monitors, scale, offsetX, offsetY, onSelectMonitor, posKeyOf, groups]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!dragging || !onMonitorsChange || !frozenTransformRef.current) return;

      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;

      const ft = frozenTransformRef.current;
      const rawX = (e.clientX - rect.left - ft.dragOffsetX - ft.offsetX) / ft.scale;
      const rawY = (e.clientY - rect.top - ft.dragOffsetY - ft.offsetY) / ft.scale;

      const bounds = computeDragBounds(dragging, monitors);
      const clampedX = Math.max(bounds.minX, Math.min(bounds.maxX, rawX));
      const clampedY = Math.max(bounds.minY, Math.min(bounds.maxY, rawY));

      const { x: snappedX, y: snappedY, guides } = computeSnap(dragging, dragGroupIdsRef.current, clampedX, clampedY, monitors, ft.scale);

      setSnapGuides(guides);

      // Move all monitors in the frozen drag group together
      const updated = monitors.map((m) => {
        if (!dragGroupIdsRef.current.has(m.id)) return m;
        return { ...m, x: Math.round(snappedX), y: Math.round(snappedY) };
      });
      onMonitorsChange(updated);
    },
    [dragging, monitors, onMonitorsChange]
  );

  const handleMouseUp = useCallback(() => {
    setDragging(null);
    dragGroupIdsRef.current = new Set();
    setSnapGuides([]);
    frozenTransformRef.current = null;
  }, []);

  const handleCanvasClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === containerRef.current) onSelectMonitor?.(null);
    },
    [onSelectMonitor]
  );

  const connected = monitorsAreConnected(monitors);

  return (
    <div
      ref={containerRef}
      className={`relative overflow-hidden rounded-fluent-lg bg-[var(--canvas-bg)] ${className}`}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onClick={handleCanvasClick}
    >
      {/* Dot grid */}
      <div
        className="absolute inset-0 opacity-[0.04] pointer-events-none"
        style={{
          backgroundImage: 'radial-gradient(circle, currentColor 1px, transparent 1px)',
          backgroundSize: '24px 24px',
        }}
      />

      {/* Edit / status badge */}
      {editable && (
        <div className="absolute top-2 left-2 flex items-center gap-2 pointer-events-none z-30">
          <div className="px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-accent/10 text-accent">
            Edit -- drag to reposition
          </div>
          {!connected && monitors.length > 1 && (
            <div className="px-2 py-0.5 rounded text-[10px] font-medium uppercase tracking-wider bg-orange-500/15 text-orange-400">
              Monitors not touching -- cannot save
            </div>
          )}
        </div>
      )}

      {/* Snap guide lines */}
      {snapGuides.map((guide, i) => {
        if (guide.type === 'vertical') {
          return (
            <div
              key={i}
              className="absolute top-0 bottom-0 w-px bg-accent/70 pointer-events-none z-40"
              style={{ left: guide.monitorCoord * scale + offsetX }}
            />
          );
        }
        return (
          <div
            key={i}
            className="absolute left-0 right-0 h-px bg-accent/70 pointer-events-none z-40"
            style={{ top: guide.monitorCoord * scale + offsetY }}
          />
        );
      })}

      {/* Monitor boxes — one per unique position group */}
      {Array.from(groups.entries()).map(([key, groupMonitors], groupIndex) => {
        const monitor = groupMonitors[0];
        const isDragged = dragging !== null && groupMonitors.some((m) => m.id === dragging);
        const overlapping = isDragged && hasOverlap(monitors, monitor.id);
        const isSelected = groupMonitors.some((m) => m.id === selectedMonitorId);
        const isHovered = groupMonitors.some((m) => m.id === hoveredId);

        return (
          <MonitorBox
            key={key}
            monitor={monitor}
            groupMonitors={groupMonitors}
            index={groupIndex}
            scale={scale}
            offsetX={offsetX}
            offsetY={offsetY}
            isSelected={isSelected}
            isHovered={isHovered}
            isDragged={isDragged}
            editable={editable}
            overlapping={overlapping}
            onMouseDown={(e) => handleMouseDown(e, monitor.id)}
            onMouseEnter={() => setHoveredId(monitor.id)}
            onMouseLeave={() => setHoveredId(null)}
          />
        );
      })}

      {monitors.length === 0 && (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <p className="text-body text-text-tertiary">No monitors detected</p>
        </div>
      )}
    </div>
  );
}
