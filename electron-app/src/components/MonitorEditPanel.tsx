import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, Star } from 'lucide-react';
import { Tooltip } from '@/components/Tooltip';
import type { Monitor } from '@/types';

interface MonitorEditPanelProps {
  monitors: Monitor[];
  selectedMonitorId: string | null;
  onSelectMonitor: (id: string | null) => void;
  onMonitorChange: (id: string, changes: Partial<Monitor>) => void;
  onSetPrimary: (id: string) => void;
  onSplitToExtended?: (monitorId: string) => void;
  onCloneWith?: (monitorId: string, targetId: string) => void;
}

const COMMON_RESOLUTIONS = [
  { label: '4K UHD', width: 3840, height: 2160 },
  { label: 'QHD', width: 2560, height: 1440 },
  { label: 'FHD', width: 1920, height: 1080 },
  { label: 'HD+', width: 1600, height: 900 },
  { label: 'HD', width: 1366, height: 768 },
  { label: 'WQHD UW', width: 3440, height: 1440 },
  { label: '5K UW', width: 5120, height: 2160 },
];

const COMMON_REFRESH_RATES = [60, 75, 100, 120, 144, 165, 180, 240, 360];

// portrait=true means the rectangle is taller than wide (width/height swapped).
const ROTATION_OPTIONS: Array<{ value: number; label: string; portrait: boolean }> = [
  { value: 0,   label: '0',   portrait: false },
  { value: 90,  label: '90',  portrait: true  },
  { value: 180, label: '180', portrait: false },
  { value: 270, label: '270', portrait: true  },
];

const SCALE_OPTIONS = [
  { value: 1.0, label: '100%' },
  { value: 1.25, label: '125%' },
  { value: 1.5, label: '150%' },
  { value: 1.75, label: '175%' },
  { value: 2.0, label: '200%' },
  { value: 2.5, label: '250%' },
  { value: 3.0, label: '300%' },
];

function FieldLabel({ text, tooltip }: { text: string; tooltip?: string }) {
  return (
    <div className="flex items-center gap-1.5 mb-1">
      <span className="text-caption text-text-tertiary">{text}</span>
      {tooltip && <Tooltip content={tooltip} />}
    </div>
  );
}

function SelectField({ label, tooltip, value, options, onChange }: {
  label: string;
  tooltip?: string;
  value: string;
  options: Array<{ value: string; label: string }>;
  onChange: (value: string) => void;
}) {
  return (
    <div>
      <FieldLabel text={label} tooltip={tooltip} />
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full h-8 px-2 rounded-fluent border border-border-default bg-[var(--input-bg)] text-body text-text-primary outline-none focus:border-accent cursor-pointer"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    </div>
  );
}

function NumberField({ label, tooltip, value, onChange, suffix, min, max, step }: {
  label: string;
  tooltip?: string;
  value: number;
  onChange: (value: number) => void;
  suffix?: string;
  min?: number;
  max?: number;
  step?: number;
}) {
  return (
    <div>
      <FieldLabel text={label} tooltip={tooltip} />
      <div className="flex items-center gap-1">
        <input
          type="number"
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          min={min}
          max={max}
          step={step}
          className="w-full h-8 px-2 rounded-fluent border border-border-default bg-[var(--input-bg)] text-body text-text-primary outline-none focus:border-accent [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
        />
        {suffix && <span className="text-caption text-text-tertiary shrink-0">{suffix}</span>}
      </div>
    </div>
  );
}

function MonitorCard({ monitor, allMonitors, isSelected, isExpanded, onSelect, onToggle, onMonitorChange, onSetPrimary, onSplitToExtended, onCloneWith }: {
  monitor: Monitor;
  allMonitors: Monitor[];
  isSelected: boolean;
  isExpanded: boolean;
  onSelect: () => void;
  onToggle: () => void;
  onMonitorChange: (changes: Partial<Monitor>) => void;
  onSetPrimary: () => void;
  onSplitToExtended?: () => void;
  onCloneWith?: (targetId: string) => void;
}) {
  const duplicatePartners = allMonitors.filter(
    (m) => m.id !== monitor.id &&
      m.x === monitor.x && m.y === monitor.y &&
      m.width === monitor.width && m.height === monitor.height
  );
  const isDuplicate = duplicatePartners.length > 0;

  const currentResKey = `${monitor.width}x${monitor.height}`;

  const resolutionOptions = COMMON_RESOLUTIONS.map((r) => ({
    value: `${r.width}x${r.height}`,
    label: `${r.width}x${r.height} (${r.label})`,
  }));

  if (!resolutionOptions.find((r) => r.value === currentResKey)) {
    resolutionOptions.unshift({
      value: currentResKey,
      label: `${monitor.width}x${monitor.height} (Current)`,
    });
  }

  const handleResolutionChange = (val: string) => {
    const [w, h] = val.split('x').map(Number);
    onMonitorChange({ width: w, height: h });
  };

  return (
    <div
      className={`
        rounded-fluent-lg border overflow-hidden transition-colors duration-150
        ${isSelected ? 'border-accent' : 'border-border-subtle'}
      `}
    >
      {/* Header */}
      <button
        onClick={() => { onSelect(); onToggle(); }}
        className={`
          w-full flex items-center justify-between px-4 py-3 cursor-pointer
          transition-colors duration-100
          ${isExpanded ? 'bg-[var(--nav-active-bg)]' : 'hover:bg-[var(--nav-hover-bg)]'}
        `}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className={`
            w-8 h-8 rounded-fluent flex items-center justify-center text-caption font-semibold
            ${monitor.isPrimary ? 'bg-accent/15 text-accent' : 'bg-[var(--badge-bg)] text-text-secondary'}
          `}>
            {monitor.isPrimary ? <Star size={14} /> : (COMMON_RESOLUTIONS.find((r) => r.width === monitor.width && r.height === monitor.height)?.label.charAt(0) ?? 'M')}
          </div>
          <div className="text-left min-w-0">
            <p className="text-body font-medium text-text-primary truncate">{monitor.name}</p>
            <p className="text-caption text-text-tertiary">
              {monitor.width}x{monitor.height} @ {monitor.refreshRate}Hz
              {monitor.isPrimary ? ' -- Primary' : ''}
            </p>
          </div>
        </div>
        {isExpanded ? <ChevronUp size={16} className="text-text-tertiary" /> : <ChevronDown size={16} className="text-text-tertiary" />}
      </button>

      {/* Expanded edit form */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 pt-1 space-y-3 border-t border-border-subtle">
              {/* Primary toggle */}
              <button
                onClick={onSetPrimary}
                disabled={monitor.isPrimary}
                className={`
                  w-full flex items-center gap-2 px-3 py-2 rounded-fluent text-body cursor-pointer
                  transition-colors duration-150 border
                  ${monitor.isPrimary
                    ? 'border-accent/30 bg-accent/5 text-accent cursor-default'
                    : 'border-border-subtle text-text-secondary hover:border-accent hover:text-accent'
                  }
                `}
              >
                <Star size={14} />
                {monitor.isPrimary ? 'Primary Monitor' : 'Set as Primary'}
              </button>

              {/* Display mode */}
              {allMonitors.length > 1 && (
                <div>
                  <FieldLabel
                    text="Display Mode"
                    tooltip="Extended: this monitor shows its own unique content. Duplicate: this monitor mirrors another monitor showing the same image."
                  />
                  <div className={`px-3 py-2 rounded-fluent border text-body mb-2 ${isDuplicate ? 'border-accent/40 bg-accent/5' : 'border-border-subtle'}`}>
                    {isDuplicate ? (
                      <>
                        <span className="font-medium text-accent">Duplicate</span>
                        <span className="text-text-tertiary text-caption ml-1.5">
                          with {duplicatePartners.map((m) => m.name).join(', ')}
                        </span>
                      </>
                    ) : (
                      <span className="font-medium text-text-primary">Extended</span>
                    )}
                  </div>

                  <div className="flex flex-col gap-2">
                    {isDuplicate && onSplitToExtended && (
                      <button
                        onClick={onSplitToExtended}
                        className="w-full py-1.5 rounded-fluent border border-border-subtle text-body text-text-secondary hover:border-accent/50 hover:text-text-primary transition-colors cursor-pointer"
                      >
                        Split to Extended
                      </button>
                    )}

                    {onCloneWith && (
                      <div>
                        <FieldLabel text="Clone with" />
                        <select
                          value={duplicatePartners[0]?.id ?? ''}
                          onChange={(e) => {
                            if (e.target.value) onCloneWith(e.target.value);
                          }}
                          className="w-full h-8 px-2 rounded-fluent border border-border-default bg-[var(--input-bg)] text-body text-text-primary outline-none focus:border-accent cursor-pointer"
                        >
                          <option value="" disabled>Select monitor...</option>
                          {allMonitors
                            .filter((m) => m.id !== monitor.id)
                            .map((m) => (
                              <option key={m.id} value={m.id}>{m.name}</option>
                            ))}
                        </select>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Resolution */}
              <SelectField
                label="Resolution"
                tooltip="The number of pixels the display outputs horizontally and vertically. Higher resolution produces a sharper, more detailed image but requires more GPU power."
                value={currentResKey}
                options={resolutionOptions}
                onChange={handleResolutionChange}
              />

              {/* Refresh rate */}
              <SelectField
                label="Refresh Rate"
                tooltip="How many times per second the display redraws the image. Higher rates (144Hz+) produce smoother motion, especially in games and fast-scrolling content."
                value={monitor.refreshRate.toString()}
                options={
                  (COMMON_REFRESH_RATES.includes(monitor.refreshRate)
                    ? COMMON_REFRESH_RATES
                    : [monitor.refreshRate, ...COMMON_REFRESH_RATES].sort((a, b) => a - b)
                  ).map((r) => ({ value: r.toString(), label: `${r} Hz` }))
                }
                onChange={(v) => onMonitorChange({ refreshRate: Number(v) })}
              />

              {/* Orientation */}
              <div>
                <FieldLabel text="Orientation" tooltip="The physical rotation of the display. The bar inside each option shows which edge is the top of the screen content. Portrait modes rotate the display 90 or 270 degrees for a vertical layout." />
                <div className="grid grid-cols-4 gap-2">
                  {ROTATION_OPTIONS.map((opt) => {
                    const isActive = monitor.rotation === opt.value;
                    const boxW = opt.portrait ? 26 : 42;
                    const boxH = opt.portrait ? 42 : 26;

                    return (
                      <button
                        key={opt.value}
                        onClick={() => onMonitorChange({ rotation: opt.value })}
                        title={opt.label}
                        className={`
                          flex flex-col items-center gap-1.5 py-2 px-1 rounded-fluent cursor-pointer
                          transition-all duration-150 border
                          ${isActive
                            ? 'border-accent bg-accent/10'
                            : 'border-border-subtle hover:border-border-default'
                          }
                        `}
                      >
                        {/* Screen rectangle: shape reflects landscape or portrait footprint.
                            A small accent bar marks which physical edge is the content's top. */}
                        <div
                          className={`relative rounded-sm border-2 ${isActive ? 'border-accent bg-accent/5' : 'border-[var(--border-default)] bg-[var(--monitor-bg)]'}`}
                          style={{ width: boxW, height: boxH }}
                        >
                          {/* "Top of content" edge indicator */}
                          <div
                            className={`absolute rounded-full ${isActive ? 'bg-accent' : 'bg-text-tertiary'}`}
                            style={
                              opt.value === 0   ? { top: 2,    left: '50%', transform: 'translateX(-50%)', width: '50%', height: 3 } :
                              opt.value === 90  ? { right: 2,  top: '50%',  transform: 'translateY(-50%)', width: 3,     height: '50%' } :
                              opt.value === 180 ? { bottom: 2, left: '50%', transform: 'translateX(-50%)', width: '50%', height: 3 } :
                                                  { left: 2,   top: '50%',  transform: 'translateY(-50%)', width: 3,     height: '50%' }
                            }
                          />
                        </div>
                        <span className={`text-[10px] leading-tight text-center tabular-nums ${isActive ? 'text-accent' : 'text-text-tertiary'}`}>
                          {opt.label}&deg;
                        </span>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Scale factor */}
              <SelectField
                label="Scale Factor"
                tooltip="Makes text and UI elements larger or smaller. 100% shows content at native pixel size. 150% means Windows renders at a lower resolution and scales up, making everything appear 1.5x larger."
                value={monitor.scaleFactor.toString()}
                options={
                  (SCALE_OPTIONS.find((s) => s.value === monitor.scaleFactor)
                    ? SCALE_OPTIONS
                    : [{ value: monitor.scaleFactor, label: `${Math.round(monitor.scaleFactor * 100)}%` }, ...SCALE_OPTIONS]
                  ).map((s) => ({ value: s.value.toString(), label: s.label }))
                }
                onChange={(v) => onMonitorChange({ scaleFactor: parseFloat(v) })}
              />

              {/* Position */}
              <div>
                <FieldLabel
                  text="Position"
                  tooltip="The coordinates of this monitor's top-left corner in the virtual desktop space. Monitors must be placed edge-to-edge with no gaps. X increases to the right, Y increases downward."
                />
                <div className="grid grid-cols-2 gap-2">
                  <NumberField
                    label="X"
                    value={monitor.x}
                    onChange={(v) => onMonitorChange({ x: v })}
                    step={100}
                  />
                  <NumberField
                    label="Y"
                    value={monitor.y}
                    onChange={(v) => onMonitorChange({ y: v })}
                    step={100}
                  />
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function MonitorEditPanel({ monitors, selectedMonitorId, onSelectMonitor, onMonitorChange, onSetPrimary, onSplitToExtended, onCloneWith }: MonitorEditPanelProps) {
  const [expandedId, setExpandedId] = useState<string | null>(monitors[0]?.id ?? null);

  const handleToggle = (id: string) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="space-y-2">
      {monitors.map((monitor) => (
        <MonitorCard
          key={monitor.id}
          monitor={monitor}
          allMonitors={monitors}
          isSelected={selectedMonitorId === monitor.id}
          isExpanded={expandedId === monitor.id}
          onSelect={() => onSelectMonitor(monitor.id)}
          onToggle={() => handleToggle(monitor.id)}
          onMonitorChange={(changes) => onMonitorChange(monitor.id, changes)}
          onSetPrimary={() => onSetPrimary(monitor.id)}
          onSplitToExtended={onSplitToExtended ? () => onSplitToExtended(monitor.id) : undefined}
          onCloneWith={onCloneWith ? (targetId) => onCloneWith(monitor.id, targetId) : undefined}
        />
      ))}
    </div>
  );
}
