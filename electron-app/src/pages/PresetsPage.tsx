import { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Play, Pencil, Copy, Trash2, Plus, Keyboard, Check, X,
  Save, RotateCcw, MonitorCheck, GripVertical, Search, Undo2, Redo2,
  ChevronUp, ChevronDown, ChevronsUpDown,
} from 'lucide-react';
import { usePresetStore } from '@/stores/presetStore';
import { MonitorCanvas } from '@/components/MonitorCanvas';
import { MonitorEditPanel } from '@/components/MonitorEditPanel';
import { HotkeyInput } from '@/components/HotkeyInput';
import { Tooltip } from '@/components/Tooltip';
import { ContextMenu } from '@/components/ContextMenu';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import type { Preset, Monitor } from '@/types';

function FlashCell({ value, children }: { value: unknown; children: React.ReactNode }) {
  return (
    <AnimatePresence initial={false} mode="sync">
      <motion.span
        key={String(value)}
        initial={{ backgroundColor: 'rgba(96,205,255,0.25)' }}
        animate={{ backgroundColor: 'rgba(96,205,255,0)' }}
        transition={{ duration: 0.7, ease: 'easeOut' }}
        className="block rounded-sm px-1 -mx-1"
      >
        {children}
      </motion.span>
    </AnimatePresence>
  );
}

function monitorsMatch(a: Monitor[], b: Monitor[]): boolean {
  if (a.length !== b.length) return false;
  const sortKey = (m: Monitor) => m.name + m.x + m.y;
  const sa = [...a].sort((x, y) => sortKey(x).localeCompare(sortKey(y)));
  const sb = [...b].sort((x, y) => sortKey(x).localeCompare(sortKey(y)));
  return sa.every((m, i) => {
    const n = sb[i];
    return (
      m.name === n.name &&
      m.width === n.width &&
      m.height === n.height &&
      m.x === n.x &&
      m.y === n.y &&
      m.refreshRate === n.refreshRate &&
      m.rotation === n.rotation &&
      m.isPrimary === n.isPrimary &&
      Math.abs(m.scaleFactor - n.scaleFactor) < 0.01
    );
  });
}

export function PresetsPage() {
  const {
    presets, selectedPresetId, currentDisplays, selectPreset,
    applyPreset, deletePreset, renamePreset,
    duplicatePreset, setHotkey, saveCurrentAsPreset, updatePreset, reorderPresets,
    testPresetLayout,
  } = usePresetStore();

  const [editingNameId, setEditingNameId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; preset: Preset } | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<Preset | null>(null);
  const [showNewInput, setShowNewInput] = useState(false);
  const [newName, setNewName] = useState('');
  const [search, setSearch] = useState('');
  const [tableSort, setTableSort] = useState<{ col: string; dir: 'asc' | 'desc' } | null>(null);

  const activePresetId = useMemo(() => {
    if (!currentDisplays.length) return null;
    return presets.find((p) => monitorsMatch(p.monitors, currentDisplays))?.id ?? null;
  }, [presets, currentDisplays]);

  const filteredPresets = useMemo(() => {
    const q = search.trim().toLowerCase();
    return q ? presets.filter((p) => p.name.toLowerCase().includes(q)) : presets;
  }, [presets, search]);

  const otherPresetHotkeys = useMemo(
    () => presets
      .filter((p) => p.id !== selectedPresetId && p.hotkey)
      .map((p) => p.hotkey as string),
    [presets, selectedPresetId]
  );

  // Full edit mode state
  const [editMode, setEditMode] = useState(false);
  const [editMonitors, setEditMonitors] = useState<Monitor[]>([]);
  const [editPresetName, setEditPresetName] = useState('');
  const [editPresetHotkey, setEditPresetHotkey] = useState<string | null>(null);
  const [selectedMonitorId, setSelectedMonitorId] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [layoutValid, setLayoutValid] = useState(true);
  const [discardConfirm, setDiscardConfirm] = useState(false);
  const [pendingSelectId, setPendingSelectId] = useState<string | null>(null);

  // Undo/Redo history
  const undoStack = useRef<Monitor[][]>([]);
  const redoStack = useRef<Monitor[][]>([]);

  const pushUndo = useCallback((monitors: Monitor[]) => {
    undoStack.current.push(monitors.map((m) => ({ ...m })));
    if (undoStack.current.length > 50) undoStack.current.shift();
    redoStack.current = [];
  }, []);

  const handleUndo = useCallback(() => {
    const prev = undoStack.current.pop();
    if (!prev) return;
    redoStack.current.push(editMonitors.map((m) => ({ ...m })));
    setEditMonitors(prev);
    setHasChanges(true);
  }, [editMonitors]);

  const handleRedo = useCallback(() => {
    const next = redoStack.current.pop();
    if (!next) return;
    undoStack.current.push(editMonitors.map((m) => ({ ...m })));
    setEditMonitors(next);
    setHasChanges(true);
  }, [editMonitors]);

  // Drag-to-reorder state
  const [dragId, setDragId] = useState<string | null>(null);
  const [dragOverId, setDragOverId] = useState<string | null>(null);
  const dragListRef = useRef<string[]>([]);

  const handleDragStart = useCallback((id: string) => {
    setDragId(id);
    dragListRef.current = presets.map((p) => p.id);
  }, [presets]);

  const handleDragOver = useCallback((id: string) => {
    if (!dragId || id === dragId) return;
    setDragOverId(id);
    const list = [...dragListRef.current];
    const fromIdx = list.indexOf(dragId);
    const toIdx = list.indexOf(id);
    if (fromIdx < 0 || toIdx < 0) return;
    list.splice(fromIdx, 1);
    list.splice(toIdx, 0, dragId);
    dragListRef.current = list;
    reorderPresets(list);
  }, [dragId, reorderPresets]);

  const handleDragEnd = useCallback(() => {
    setDragId(null);
    setDragOverId(null);
  }, []);

  const selectedPreset = presets.find((p) => p.id === selectedPresetId);

  const enterEditMode = useCallback((preset: Preset) => {
    undoStack.current = [];
    redoStack.current = [];
    setEditMode(true);
    setEditMonitors(preset.monitors.map((m) => ({ ...m })));
    setEditPresetName(preset.name);
    setEditPresetHotkey(preset.hotkey);
    setSelectedMonitorId(preset.monitors[0]?.id ?? null);
    setHasChanges(false);
  }, []);

  const exitEditMode = useCallback(() => {
    undoStack.current = [];
    redoStack.current = [];
    setEditMode(false);
    setEditMonitors([]);
    setEditPresetName('');
    setEditPresetHotkey(null);
    setSelectedMonitorId(null);
    setHasChanges(false);
  }, []);

  const handleSaveEdit = useCallback(() => {
    if (!selectedPreset) return;
    updatePreset(selectedPreset.id, {
      name: editPresetName,
      hotkey: editPresetHotkey,
      monitors: editMonitors,
    });
    exitEditMode();
  }, [selectedPreset, editPresetName, editPresetHotkey, editMonitors, updatePreset, exitEditMode]);

  const handleResetEdit = useCallback(() => {
    if (!selectedPreset) return;
    setEditMonitors(selectedPreset.monitors.map((m) => ({ ...m })));
    setEditPresetName(selectedPreset.name);
    setEditPresetHotkey(selectedPreset.hotkey);
    setHasChanges(false);
  }, [selectedPreset]);

  const handleMonitorChange = useCallback((id: string, changes: Partial<Monitor>) => {
    setEditMonitors((prev) => {
      pushUndo(prev);
      return prev.map((m) => (m.id === id ? { ...m, ...changes } : m));
    });
    setHasChanges(true);
  }, [pushUndo]);

  const handleSetPrimary = useCallback((id: string) => {
    setEditMonitors((prev) => {
      pushUndo(prev);
      const target = prev.find((m) => m.id === id);
      if (!target) return prev;
      // All monitors at the same position (duplicate group) must share primary status
      return prev.map((m) => ({
        ...m,
        isPrimary:
          m.x === target.x &&
          m.y === target.y &&
          m.width === target.width &&
          m.height === target.height,
      }));
    });
    setHasChanges(true);
  }, [pushUndo]);

  const handleSplitToExtended = useCallback((monitorId: string) => {
    setEditMonitors((prev) => {
      pushUndo(prev);
      const nextX = Math.max(...prev.map((m) => m.x + m.width), 0);
      // Split monitor loses primary — it is no longer in the primary group
      const updated = prev.map((m) =>
        m.id === monitorId ? { ...m, x: nextX, y: 0, isPrimary: false } : m
      );
      // Safety: if all primaries moved away, make the first remaining monitor primary
      if (!updated.some((m) => m.isPrimary)) {
        const first = updated.find((m) => m.id !== monitorId) ?? updated[0];
        return updated.map((m) => ({ ...m, isPrimary: m.id === first?.id }));
      }
      return updated;
    });
    setHasChanges(true);
  }, [pushUndo]);

  const handleCloneWith = useCallback((monitorId: string, targetId: string) => {
    setEditMonitors((prev) => {
      pushUndo(prev);
      const target = prev.find((m) => m.id === targetId);
      if (!target) return prev;
      const { x, y, width, height, rotation, refreshRate } = target;
      // Target group's primary status determines the merged group's primary status
      const groupIsPrimary = prev.some(
        (m) => m.x === x && m.y === y && m.width === width && m.height === height && m.isPrimary
      );
      const updated = prev.map((m) =>
        m.id === monitorId
          ? { ...m, x, y, width, height, rotation, refreshRate, isPrimary: groupIsPrimary }
          : m
      );
      // Safety: if all primaries were moved away, make first monitor primary
      if (!updated.some((m) => m.isPrimary)) {
        return updated.map((m, i) => ({ ...m, isPrimary: i === 0 }));
      }
      return updated;
    });
    setHasChanges(true);
  }, [pushUndo]);

  const handleCanvasMonitorsChange = useCallback((monitors: Monitor[]) => {
    setEditMonitors((prev) => {
      pushUndo(prev);
      return monitors;
    });
    setHasChanges(true);
  }, [pushUndo]);

  const handleSelectPreset = useCallback((id: string) => {
    if (editMode && hasChanges) {
      setPendingSelectId(id);
      setDiscardConfirm(true);
      return;
    }
    if (editMode) exitEditMode();
    selectPreset(id);
  }, [editMode, hasChanges, exitEditMode, selectPreset]);

  const handleDoubleClick = useCallback((id: string) => {
    if (editMode) return;
    applyPreset(id);
  }, [editMode, applyPreset]);

  const startRename = (preset: Preset) => {
    setEditingNameId(preset.id);
    setEditName(preset.name);
  };

  const commitRename = () => {
    if (editingNameId && editName.trim()) {
      renamePreset(editingNameId, editName.trim());
    }
    setEditingNameId(null);
  };

  const handleContextMenu = (e: React.MouseEvent, preset: Preset) => {
    e.preventDefault();
    if (!editMode) selectPreset(preset.id);
    setContextMenu({ x: e.clientX, y: e.clientY, preset });
  };

  const handleCreateNew = () => {
    if (newName.trim()) {
      saveCurrentAsPreset(newName.trim());
      setNewName('');
      setShowNewInput(false);
    }
  };

  // Tray IPC events
  useEffect(() => {
    if (!window.api) return;
    const unsubApply = window.api.onApplyPreset((presetId) => {
      applyPreset(presetId);
    });
    const unsubSave = window.api.onSaveCurrentConfig(() => {
      setShowNewInput(true);
    });
    return () => { unsubApply(); unsubSave(); };
  }, [applyPreset]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      const isInput = tag === 'INPUT' || tag === 'TEXTAREA';

      if (editMode) {
        if (e.ctrlKey && e.key === 'z' && !isInput) { e.preventDefault(); handleUndo(); return; }
        if (e.ctrlKey && e.key === 'y' && !isInput) { e.preventDefault(); handleRedo(); return; }
        if (e.key === 'Escape' && !isInput) { exitEditMode(); return; }
        if (e.ctrlKey && e.key === 's' && !isInput) { e.preventDefault(); if (hasChanges && layoutValid) handleSaveEdit(); return; }
        return;
      }

      if (isInput) return;

      if (e.key === 'Delete' && selectedPresetId) {
        const preset = presets.find((p) => p.id === selectedPresetId);
        if (preset) setDeleteConfirm(preset);
      } else if (e.key === 'F2' && selectedPreset) {
        startRename(selectedPreset);
      } else if (e.key === 'Enter' && selectedPresetId) {
        applyPreset(selectedPresetId);
      } else if (e.key === 'd' && selectedPresetId && !e.ctrlKey && !e.altKey) {
        duplicatePreset(selectedPresetId);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [editMode, hasChanges, layoutValid, selectedPresetId, selectedPreset, presets,
    handleUndo, handleRedo, exitEditMode, handleSaveEdit, applyPreset, enterEditMode,
    duplicatePreset]);

  const displayMonitors = editMode ? editMonitors : (selectedPreset?.monitors ?? []);

  return (
    <div className="flex flex-1 h-full overflow-hidden">
      {/* Preset list */}
      <div className="w-[280px] shrink-0 flex flex-col border-r border-border-subtle">
        <div className="flex items-center justify-between px-4 py-3 border-b border-border-subtle">
          <h2 className="text-body font-semibold text-text-primary">Presets</h2>
          <button
            onClick={() => setShowNewInput(true)}
            className="p-1.5 rounded-fluent text-text-secondary hover:text-text-primary hover:bg-[var(--nav-hover-bg)] transition-colors duration-150 cursor-pointer"
            title="Save current display config"
          >
            <Plus size={16} />
          </button>
        </div>
        <div className="px-3 py-2 border-b border-border-subtle">
          <div className="flex items-center gap-2 h-7 px-2.5 rounded-fluent border border-border-default bg-[var(--input-bg)]">
            <Search size={12} className="text-text-tertiary shrink-0" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search presets..."
              className="flex-1 text-body text-text-primary placeholder:text-text-tertiary bg-transparent outline-none"
            />
            {search && (
              <button onClick={() => setSearch('')} className="text-text-tertiary hover:text-text-primary cursor-pointer">
                <X size={12} />
              </button>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-1">
          <AnimatePresence>
            {showNewInput && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="px-3 py-1.5"
              >
                <div className="flex items-center gap-1.5">
                  <input
                    autoFocus
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleCreateNew();
                      if (e.key === 'Escape') { setShowNewInput(false); setNewName(''); }
                    }}
                    placeholder="Preset name"
                    className="flex-1 h-8 px-2.5 text-body rounded-fluent border border-border-default bg-[var(--input-bg)] text-text-primary placeholder:text-text-tertiary outline-none focus:border-accent"
                  />
                  <button onClick={handleCreateNew} className="p-1.5 text-accent hover:text-accent-hover cursor-pointer">
                    <Check size={14} />
                  </button>
                  <button onClick={() => { setShowNewInput(false); setNewName(''); }} className="p-1.5 text-text-tertiary hover:text-text-primary cursor-pointer">
                    <X size={14} />
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {filteredPresets.map((preset) => {
            const isSelected = selectedPresetId === preset.id;
            const isEditingName = editingNameId === preset.id;
            const isActive = activePresetId === preset.id;
            const isDragging = dragId === preset.id;

            return (
              <motion.div
                key={preset.id}
                layout
                draggable
                onDragStart={() => handleDragStart(preset.id)}
                onDragOver={(e) => { e.preventDefault(); handleDragOver(preset.id); }}
                onDragEnd={handleDragEnd}
                onClick={() => handleSelectPreset(preset.id)}
                onDoubleClick={() => handleDoubleClick(preset.id)}
                onContextMenu={(e) => handleContextMenu(e, preset)}
                className={`
                  group mx-2 mb-0.5 px-3 py-2.5 rounded-fluent cursor-pointer
                  transition-colors duration-100
                  ${isDragging ? 'opacity-40' : ''}
                  ${dragOverId === preset.id && dragId !== preset.id ? 'border-t-2 border-accent' : ''}
                  ${isSelected
                    ? 'bg-[var(--nav-active-bg)]'
                    : 'hover:bg-[var(--nav-hover-bg)]'
                  }
                `}
              >
                {isEditingName ? (
                  <input
                    autoFocus
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') commitRename();
                      if (e.key === 'Escape') setEditingNameId(null);
                    }}
                    onBlur={commitRename}
                    className="w-full h-6 px-1.5 text-body rounded border border-accent bg-[var(--input-bg)] text-text-primary outline-none"
                    onClick={(e) => e.stopPropagation()}
                  />
                ) : (
                  <div className="flex items-center gap-2">
                    <GripVertical
                      size={14}
                      className="text-text-tertiary opacity-0 group-hover:opacity-100 transition-opacity shrink-0 cursor-grab"
                      onMouseDown={(e) => e.stopPropagation()}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-1.5">
                        <p className="text-body font-medium text-text-primary truncate">{preset.name}</p>
                        {isActive && (
                          <span title="Active — matches current display configuration">
                            <MonitorCheck size={13} className="text-green-400 shrink-0" />
                          </span>
                        )}
                      </div>
                      <p className="text-caption text-text-tertiary mt-0.5">
                        {preset.monitors.length} monitor{preset.monitors.length !== 1 ? 's' : ''}
                        {isActive && <span className="text-green-400 ml-1.5">Active</span>}
                      </p>
                    </div>
                    {preset.hotkey && (
                      <span className="shrink-0 px-1.5 py-0.5 text-[11px] font-medium rounded bg-[var(--badge-bg)] text-text-secondary">
                        {preset.hotkey}
                      </span>
                    )}
                  </div>
                )}
              </motion.div>
            );
          })}

          {presets.length === 0 && !showNewInput && (
            <div className="px-4 py-8 text-center">
              <p className="text-body text-text-tertiary">No presets yet</p>
              <button
                onClick={() => setShowNewInput(true)}
                className="mt-2 text-body text-accent hover:text-accent-hover cursor-pointer"
              >
                Save current config
              </button>
            </div>
          )}
          {presets.length > 0 && filteredPresets.length === 0 && (
            <div className="px-4 py-8 text-center">
              <p className="text-body text-text-tertiary">No results for "{search}"</p>
            </div>
          )}
        </div>
      </div>

      {/* Detail / Edit panel */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <AnimatePresence mode="wait">
          {selectedPreset ? (
            <motion.div
              key={editMode ? `${selectedPreset.id}-edit` : selectedPreset.id}
              initial={{ opacity: 0, x: 12 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -12 }}
              transition={{ duration: 0.15 }}
              className="flex-1 flex flex-col overflow-hidden"
            >
              {/* Toolbar */}
              <div className="flex items-center justify-between px-5 py-3 border-b border-border-subtle shrink-0">
                <div className="min-w-0">
                  {editMode ? (
                    <input
                      value={editPresetName}
                      onChange={(e) => { setEditPresetName(e.target.value); setHasChanges(true); }}
                      className="text-title font-semibold bg-transparent text-text-primary outline-none border-b-2 border-accent pb-0.5 w-64"
                    />
                  ) : (
                    <h2 className="text-title font-semibold text-text-primary truncate">{selectedPreset.name}</h2>
                  )}
                  <p className="text-caption text-text-tertiary mt-0.5">
                    {displayMonitors.length} monitor{displayMonitors.length !== 1 ? 's' : ''}
                    {!editMode && ` -- Updated ${new Date(selectedPreset.updatedAt).toLocaleDateString()}`}
                    {editMode && hasChanges && ' -- Unsaved changes'}
                  </p>
                </div>
                <div className="flex gap-1.5 shrink-0">
                  {editMode ? (
                    <>
                      <button
                        onClick={handleUndo}
                        disabled={undoStack.current.length === 0}
                        title="Undo (Ctrl+Z)"
                        className="p-1.5 rounded-fluent text-text-secondary hover:text-text-primary hover:bg-[var(--nav-hover-bg)] transition-colors duration-150 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        <Undo2 size={15} />
                      </button>
                      <button
                        onClick={handleRedo}
                        disabled={redoStack.current.length === 0}
                        title="Redo (Ctrl+Y)"
                        className="p-1.5 rounded-fluent text-text-secondary hover:text-text-primary hover:bg-[var(--nav-hover-bg)] transition-colors duration-150 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        <Redo2 size={15} />
                      </button>
                      <button
                        onClick={handleResetEdit}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-fluent text-body text-text-secondary hover:text-text-primary hover:bg-[var(--nav-hover-bg)] transition-colors duration-150 cursor-pointer"
                      >
                        <RotateCcw size={14} />
                        Reset
                      </button>
                      <button
                        onClick={exitEditMode}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-fluent text-body border border-border-default text-text-primary hover:bg-[var(--nav-hover-bg)] transition-colors duration-150 cursor-pointer"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={() => testPresetLayout(selectedPreset.id, editMonitors)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-fluent text-body text-text-secondary hover:text-text-primary hover:bg-[var(--nav-hover-bg)] transition-colors duration-150 cursor-pointer"
                        title="Test layout without saving"
                      >
                        <Play size={14} />
                        Test
                      </button>
                      <button
                        onClick={handleSaveEdit}
                        disabled={!hasChanges || !layoutValid}
                        title={!layoutValid ? 'Monitors must be touching to save' : !hasChanges ? 'No changes' : undefined}
                        className={`
                          flex items-center gap-1.5 px-3 py-1.5 rounded-fluent text-body font-medium transition-colors duration-150
                          ${hasChanges && layoutValid
                            ? 'bg-accent text-[#000] hover:bg-accent-hover cursor-pointer'
                            : 'bg-accent/40 text-[#000]/50 cursor-not-allowed'
                          }
                        `}
                      >
                        <Save size={14} />
                        {!layoutValid ? 'Invalid Layout' : 'Save'}
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => applyPreset(selectedPreset.id)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-fluent bg-accent text-[#000] text-body font-medium hover:bg-accent-hover transition-colors duration-150 cursor-pointer"
                      >
                        <Play size={14} />
                        Apply
                      </button>
                      <button
                        onClick={() => duplicatePreset(selectedPreset.id)}
                        className="p-1.5 rounded-fluent text-text-secondary hover:text-text-primary hover:bg-[var(--nav-hover-bg)] transition-colors duration-150 cursor-pointer"
                        title="Duplicate"
                      >
                        <Copy size={15} />
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(selectedPreset)}
                        className="p-1.5 rounded-fluent text-text-secondary hover:text-red-400 hover:bg-red-500/10 transition-colors duration-150 cursor-pointer"
                        title="Delete"
                      >
                        <Trash2 size={15} />
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Content area */}
              <div className="flex-1 flex overflow-hidden">
                {/* Main content: canvas + details */}
                <div className={`flex-1 flex flex-col p-5 overflow-y-auto ${editMode ? 'pr-0' : ''}`}>
                  {/* Monitor preview canvas */}
                  <MonitorCanvas
                    monitors={displayMonitors}
                    editable={editMode}
                    onMonitorsChange={handleCanvasMonitorsChange}
                    onLayoutValidChange={setLayoutValid}
                    selectedMonitorId={editMode ? selectedMonitorId : null}
                    onSelectMonitor={editMode ? setSelectedMonitorId : undefined}
                    className="h-[260px] mb-5 shrink-0"
                  />

                  {!editMode && (
                    <div className="flex items-center gap-3 mb-4">
                      <Keyboard size={16} className="text-text-tertiary shrink-0" />
                      <div className="flex items-center gap-1.5 w-16 shrink-0">
                        <span className="text-body text-text-secondary">Hotkey</span>
                        <Tooltip content="Optional. A global keyboard shortcut that applies this preset instantly from anywhere, even when the app is minimized. Click the field and press any key combination to assign one." />
                      </div>
                      <HotkeyInput
                        value={selectedPreset.hotkey}
                        onChange={(hotkey) => setHotkey(selectedPreset.id, hotkey)}
                        existingHotkeys={otherPresetHotkeys}
                        className="flex-1 max-w-[280px]"
                      />
                    </div>
                  )}

                  {/* Monitor details table — always visible, updates live in edit mode */}
                  <div className="mt-2">
                    <h3 className="text-body font-medium text-text-primary mb-2">Monitor Details</h3>
                    <div className="rounded-fluent border border-border-subtle overflow-hidden">
                      <table className="w-full text-body">
                        <thead>
                          <tr className="bg-[var(--table-header-bg)] text-text-secondary text-caption">
                            {(
                              [
                                { key: 'name', label: 'Display' },
                                { key: 'resolution', label: 'Resolution' },
                                { key: 'refreshRate', label: 'Refresh' },
                                { key: 'scaleFactor', label: 'Scale' },
                                { key: 'rotation', label: 'Rotation' },
                                { key: 'position', label: 'Position' },
                                { key: 'isPrimary', label: 'Primary' },
                              ] as const
                            ).map(({ key, label }) => {
                              const active = tableSort?.col === key;
                              const Icon = active
                                ? tableSort.dir === 'asc' ? ChevronUp : ChevronDown
                                : ChevronsUpDown;
                              return (
                                <th
                                  key={key}
                                  className="text-left px-3 py-2 font-medium select-none cursor-pointer hover:text-text-primary transition-colors duration-100"
                                  onClick={() =>
                                    setTableSort((prev) =>
                                      prev?.col === key
                                        ? { col: key, dir: prev.dir === 'asc' ? 'desc' : 'asc' }
                                        : { col: key, dir: 'asc' }
                                    )
                                  }
                                >
                                  <span className="inline-flex items-center gap-1">
                                    {label}
                                    <Icon size={11} className={active ? 'text-accent' : 'opacity-40'} />
                                  </span>
                                </th>
                              );
                            })}
                          </tr>
                        </thead>
                        <tbody>
                          {[...displayMonitors]
                            .sort((a, b) => {
                              if (!tableSort) return 0;
                              const { col, dir } = tableSort;
                              const sign = dir === 'asc' ? 1 : -1;
                              if (col === 'name') return sign * a.name.localeCompare(b.name);
                              if (col === 'resolution') return sign * (a.width * a.height - b.width * b.height);
                              if (col === 'refreshRate') return sign * (a.refreshRate - b.refreshRate);
                              if (col === 'scaleFactor') return sign * (a.scaleFactor - b.scaleFactor);
                              if (col === 'rotation') return sign * (a.rotation - b.rotation);
                              if (col === 'position') return sign * (a.x !== b.x ? a.x - b.x : a.y - b.y);
                              if (col === 'isPrimary') return sign * ((a.isPrimary ? 1 : 0) - (b.isPrimary ? 1 : 0));
                              return 0;
                            })
                            .map((m) => (
                              <tr key={m.id} className="border-t border-border-subtle">
                                <td className="px-3 py-2 text-text-primary">
                                  <FlashCell value={m.name}>{m.name}</FlashCell>
                                </td>
                                <td className="px-3 py-2 text-text-secondary">
                                  <FlashCell value={`${m.width}x${m.height}`}>{m.width}x{m.height}</FlashCell>
                                </td>
                                <td className="px-3 py-2 text-text-secondary">
                                  <FlashCell value={m.refreshRate}>{m.refreshRate}Hz</FlashCell>
                                </td>
                                <td className="px-3 py-2 text-text-secondary">
                                  <FlashCell value={m.scaleFactor}>{Math.round(m.scaleFactor * 100)}%</FlashCell>
                                </td>
                                <td className="px-3 py-2 text-text-secondary">
                                  <FlashCell value={m.rotation}>{m.rotation}deg</FlashCell>
                                </td>
                                <td className="px-3 py-2 text-text-secondary">
                                  <FlashCell value={`${m.x},${m.y}`}>{m.x}, {m.y}</FlashCell>
                                </td>
                                <td className="px-3 py-2">
                                  <FlashCell value={m.isPrimary}>
                                    {m.isPrimary && <span className="text-accent font-medium">Yes</span>}
                                  </FlashCell>
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>

                {/* Edit sidebar: monitor property panels */}
                {editMode && (
                  <motion.div
                    initial={{ width: 0, opacity: 0 }}
                    animate={{ width: 320, opacity: 1 }}
                    exit={{ width: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                    className="w-[320px] shrink-0 border-l border-border-subtle overflow-y-auto p-4"
                  >
                    <h3 className="text-body font-semibold text-text-primary mb-1">Monitors</h3>
                    <p className="text-caption text-text-tertiary mb-3">
                      Click a monitor on the canvas or expand below to edit
                    </p>

                    <MonitorEditPanel
                      monitors={editMonitors}
                      selectedMonitorId={selectedMonitorId}
                      onSelectMonitor={setSelectedMonitorId}
                      onMonitorChange={handleMonitorChange}
                      onSetPrimary={handleSetPrimary}
                      onSplitToExtended={handleSplitToExtended}
                      onCloneWith={handleCloneWith}
                    />

                    {/* Hotkey in edit mode */}
                    <div className="mt-4 pt-4 border-t border-border-subtle">
                      <div className="flex items-center gap-2 mb-2">
                        <Keyboard size={14} className="text-text-tertiary" />
                        <span className="text-body font-medium text-text-primary">Hotkey</span>
                        <Tooltip content="Optional. A global keyboard shortcut that applies this preset instantly from anywhere, even when the app is minimized. Click the field and press any key combination to assign one." />
                      </div>
                      <HotkeyInput
                        value={editPresetHotkey}
                        onChange={(hotkey) => { setEditPresetHotkey(hotkey); setHasChanges(true); }}
                        existingHotkeys={otherPresetHotkeys}
                      />
                    </div>
                  </motion.div>
                )}
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex-1 flex items-center justify-center"
            >
              <p className="text-body text-text-tertiary">Select a preset to view details</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Context menu */}
      {contextMenu && (
        <ContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={() => setContextMenu(null)}
          items={[
            { label: 'Apply', icon: <Play size={14} />, onClick: () => applyPreset(contextMenu.preset.id) },
            { label: 'Rename', icon: <Pencil size={14} />, onClick: () => startRename(contextMenu.preset) },
            { label: 'Duplicate', icon: <Copy size={14} />, onClick: () => duplicatePreset(contextMenu.preset.id) },
            { label: '', onClick: () => {}, separator: true },
            { label: 'Delete', icon: <Trash2 size={14} />, onClick: () => setDeleteConfirm(contextMenu.preset), danger: true },
          ]}
        />
      )}

      {/* Delete confirmation */}
      <ConfirmDialog
        open={deleteConfirm !== null}
        title="Delete Preset"
        message={`Are you sure you want to delete "${deleteConfirm?.name}"? This cannot be undone.`}
        confirmLabel="Delete"
        danger
        onConfirm={() => {
          if (deleteConfirm) deletePreset(deleteConfirm.id);
          setDeleteConfirm(null);
          if (editMode) exitEditMode();
        }}
        onCancel={() => setDeleteConfirm(null)}
      />

      {/* Discard changes confirmation */}
      <ConfirmDialog
        open={discardConfirm}
        title="Unsaved Changes"
        message="You have unsaved changes. Discard them and switch presets?"
        confirmLabel="Discard"
        danger
        onConfirm={() => {
          exitEditMode();
          if (pendingSelectId) {
            selectPreset(pendingSelectId);
            setPendingSelectId(null);
          }
          setDiscardConfirm(false);
        }}
        onCancel={() => { setDiscardConfirm(false); setPendingSelectId(null); }}
      />
    </div>
  );
}
