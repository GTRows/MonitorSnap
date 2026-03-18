import { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Save, RotateCcw, Play, FilePlus } from 'lucide-react';
import { usePresetStore } from '@/stores/presetStore';
import { MonitorCanvas } from '@/components/MonitorCanvas';
import type { Monitor } from '@/types';

export function DisplaysPage() {
  const { currentDisplays, saveCurrentAsPreset, testDisplayLayout, fetchCurrentDisplays } = usePresetStore();
  const [editMode, setEditMode] = useState(false);
  const [editMonitors, setEditMonitors] = useState<Monitor[]>([]);
  const [showSaveInput, setShowSaveInput] = useState(false);
  const [saveName, setSaveName] = useState('');

  const activeMonitors = editMode ? editMonitors : currentDisplays;

  const enterEditMode = useCallback(() => {
    setEditMonitors([...currentDisplays]);
    setEditMode(true);
  }, [currentDisplays]);

  const resetEdit = useCallback(() => {
    setEditMonitors([...currentDisplays]);
  }, [currentDisplays]);

  const exitEditMode = useCallback(() => {
    setEditMode(false);
    setEditMonitors([]);
  }, []);

  const handleTestLayout = useCallback(async () => {
    await testDisplayLayout(editMonitors);
  }, [editMonitors, testDisplayLayout]);

  const handleSaveLayout = useCallback(async () => {
    const ok = await testDisplayLayout(editMonitors);
    if (ok) {
      await fetchCurrentDisplays();
      exitEditMode();
    }
  }, [editMonitors, testDisplayLayout, fetchCurrentDisplays, exitEditMode]);

  const handleSaveAs = () => {
    if (saveName.trim()) {
      saveCurrentAsPreset(saveName.trim());
      setSaveName('');
      setShowSaveInput(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="flex-1 flex flex-col p-5 overflow-y-auto"
    >
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-title font-semibold text-text-primary">Current Displays</h2>
          <p className="text-caption text-text-tertiary mt-1">
            {currentDisplays.length} monitor{currentDisplays.length !== 1 ? 's' : ''} detected
          </p>
        </div>

        <div className="flex gap-1.5">
          {editMode ? (
            <>
              <button
                onClick={resetEdit}
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
                onClick={handleTestLayout}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-fluent text-body text-text-secondary hover:text-text-primary hover:bg-[var(--nav-hover-bg)] transition-colors duration-150 cursor-pointer"
              >
                <Play size={14} />
                Test Layout
              </button>
              <button
                onClick={handleSaveLayout}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-fluent bg-accent text-[#000] text-body font-medium hover:bg-accent-hover transition-colors duration-150 cursor-pointer"
              >
                <Save size={14} />
                Apply
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => setShowSaveInput(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-fluent text-body text-text-secondary hover:text-text-primary hover:bg-[var(--nav-hover-bg)] transition-colors duration-150 cursor-pointer"
              >
                <FilePlus size={14} />
                Save as Preset
              </button>
              <button
                onClick={enterEditMode}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-fluent bg-accent text-[#000] text-body font-medium hover:bg-accent-hover transition-colors duration-150 cursor-pointer"
              >
                Edit Layout
              </button>
            </>
          )}
        </div>
      </div>

      {/* Save as input */}
      {showSaveInput && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: 'auto' }}
          className="mb-4 flex items-center gap-2"
        >
          <input
            autoFocus
            value={saveName}
            onChange={(e) => setSaveName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSaveAs();
              if (e.key === 'Escape') { setShowSaveInput(false); setSaveName(''); }
            }}
            placeholder="Enter preset name"
            className="h-8 w-64 px-2.5 text-body rounded-fluent border border-border-default bg-[var(--input-bg)] text-text-primary placeholder:text-text-tertiary outline-none focus:border-accent"
          />
          <button
            onClick={handleSaveAs}
            className="px-3 py-1.5 text-body rounded-fluent bg-accent text-[#000] font-medium hover:bg-accent-hover transition-colors cursor-pointer"
          >
            Save
          </button>
          <button
            onClick={() => { setShowSaveInput(false); setSaveName(''); }}
            className="px-3 py-1.5 text-body rounded-fluent text-text-secondary hover:text-text-primary cursor-pointer"
          >
            Cancel
          </button>
        </motion.div>
      )}

      {/* Canvas */}
      <MonitorCanvas
        monitors={activeMonitors}
        editable={editMode}
        onMonitorsChange={setEditMonitors}
        className="flex-1 min-h-[300px]"
      />

      {/* Monitor details table */}
      <div className="mt-5 rounded-fluent-lg border border-border-subtle overflow-hidden">
        <table className="w-full text-body">
          <thead>
            <tr className="bg-surface-raised text-text-tertiary text-caption">
              <th className="text-left font-medium px-4 py-2.5">#</th>
              <th className="text-left font-medium px-4 py-2.5">Name</th>
              <th className="text-left font-medium px-4 py-2.5">Connector</th>
              <th className="text-left font-medium px-4 py-2.5">Resolution</th>
              <th className="text-left font-medium px-4 py-2.5">Refresh Rate</th>
              <th className="text-left font-medium px-4 py-2.5">Scale</th>
              <th className="text-left font-medium px-4 py-2.5">Position</th>
              <th className="text-left font-medium px-4 py-2.5">Rotation</th>
              <th className="text-left font-medium px-4 py-2.5">Color</th>
            </tr>
          </thead>
          <tbody>
            {activeMonitors.map((m, idx) => (
              <tr
                key={m.id}
                className={`
                  border-t border-border-subtle transition-colors duration-100
                  ${m.isPrimary ? 'bg-accent/5' : 'hover:bg-surface-raised/50'}
                `}
              >
                <td className="px-4 py-2.5 text-text-tertiary tabular-nums">{idx + 1}</td>
                <td className="px-4 py-2.5">
                  <div className="flex items-center gap-2">
                    <span className="text-text-primary font-medium truncate max-w-[180px]">{m.name}</span>
                    {m.isPrimary && (
                      <span className="shrink-0 text-[10px] font-semibold text-accent bg-accent/10 px-1.5 py-0.5 rounded uppercase tracking-wider">
                        Primary
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-2.5 text-text-secondary">{m.connector ?? '--'}</td>
                <td className="px-4 py-2.5 text-text-secondary tabular-nums">
                  {m.width}x{m.height}
                  {m.nativeWidth && m.nativeHeight && (m.nativeWidth !== m.width || m.nativeHeight !== m.height) && (
                    <span className="text-text-tertiary text-caption ml-1">
                      (native {m.nativeWidth}x{m.nativeHeight})
                    </span>
                  )}
                </td>
                <td className="px-4 py-2.5 text-text-secondary tabular-nums">{m.refreshRate} Hz</td>
                <td className="px-4 py-2.5 text-text-secondary tabular-nums">{Math.round(m.scaleFactor * 100)}%</td>
                <td className="px-4 py-2.5 text-text-secondary tabular-nums">{m.x}, {m.y}</td>
                <td className="px-4 py-2.5 text-text-secondary">{m.rotation === 0 ? 'Landscape' : `${m.rotation}deg`}</td>
                <td className="px-4 py-2.5 text-text-secondary">{m.colorDepth ?? '--'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </motion.div>
  );
}
