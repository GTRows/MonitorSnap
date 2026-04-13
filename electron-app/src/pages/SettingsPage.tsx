import { useState } from 'react';
import { motion } from 'framer-motion';
import { Sun, Moon, Monitor, Download, Upload, RotateCcw, Trash2, FlaskConical } from 'lucide-react';
import { useSettingsStore } from '@/stores/settingsStore';
import { usePresetStore } from '@/stores/presetStore';
import { Toggle } from '@/components/Toggle';
import { ConfirmDialog } from '@/components/ConfirmDialog';

function SectionHeader({ title }: { title: string }) {
  return (
    <h3 className="text-body font-semibold text-text-primary mb-3 mt-6 first:mt-0">{title}</h3>
  );
}

function SettingRow({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-2.5 min-h-[44px]">
      <div className="mr-4">
        <p className="text-body text-text-primary">{label}</p>
        {description && <p className="text-caption text-text-tertiary mt-0.5">{description}</p>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  );
}

export function SettingsPage() {
  const { settings, updateSettings, resetSettings } = useSettingsStore();
  const { presets, exportPresets, importPresets, clearAllPresets } = usePresetStore();
  const [showFactoryReset, setShowFactoryReset] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="flex-1 p-5 overflow-y-auto"
    >
      <h2 className="text-title font-semibold text-text-primary mb-1">Settings</h2>
      <p className="text-caption text-text-tertiary mb-4">Configure application preferences</p>

      <div className="max-w-[600px]">
        {/* Appearance */}
        <SectionHeader title="Appearance" />
        <div className="rounded-fluent-lg border border-border-subtle overflow-hidden">
          <div className="p-3">
            <p className="text-body text-text-primary mb-3">Theme</p>
            <div className="flex gap-2">
              {([
                { value: 'light' as const, label: 'Light', icon: Sun },
                { value: 'dark' as const, label: 'Dark', icon: Moon },
                { value: 'system' as const, label: 'System', icon: Monitor },
              ]).map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  onClick={() => updateSettings({ theme: value })}
                  className={`
                    flex items-center gap-2 px-4 py-2 rounded-fluent text-body cursor-pointer
                    transition-all duration-150 border
                    ${settings.theme === value
                      ? 'border-accent bg-accent/10 text-text-primary'
                      : 'border-border-subtle text-text-secondary hover:border-border-default hover:text-text-primary'
                    }
                  `}
                >
                  <Icon size={16} />
                  {label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Startup */}
        <SectionHeader title="Startup" />
        <div className="rounded-fluent-lg border border-border-subtle divide-y divide-border-subtle">
          <div className="px-4">
            <SettingRow label="Start with Windows" description="Launch automatically on login">
              <Toggle
                checked={settings.startWithWindows}
                onChange={(v) => updateSettings({ startWithWindows: v })}
              />
            </SettingRow>
          </div>
          <div className="px-4">
            <SettingRow label="Start minimized" description="Open in system tray">
              <Toggle
                checked={settings.startMinimized}
                onChange={(v) => updateSettings({ startMinimized: v })}
              />
            </SettingRow>
          </div>
        </div>

        {/* Behavior */}
        <SectionHeader title="Behavior" />
        <div className="rounded-fluent-lg border border-border-subtle divide-y divide-border-subtle">
          <div className="px-4">
            <SettingRow label="Minimize after apply" description="Hide window after applying a preset">
              <Toggle
                checked={settings.minimizeAfterApply}
                onChange={(v) => updateSettings({ minimizeAfterApply: v })}
              />
            </SettingRow>
          </div>
          <div className="px-4">
            <SettingRow label="ESC to minimize" description="Press Escape to minimize to tray">
              <Toggle
                checked={settings.escToMinimize}
                onChange={(v) => updateSettings({ escToMinimize: v })}
              />
            </SettingRow>
          </div>
        </div>

        {/* Notifications */}
        <SectionHeader title="Notifications" />
        <div className="rounded-fluent-lg border border-border-subtle">
          <div className="px-4">
            <SettingRow label="Show notifications" description="Display toast when presets are applied">
              <Toggle
                checked={settings.notifications}
                onChange={(v) => updateSettings({ notifications: v })}
              />
            </SettingRow>
          </div>
        </div>

        {/* Advanced */}
        <SectionHeader title="Advanced" />
        <div className="rounded-fluent-lg border border-border-subtle divide-y divide-border-subtle">
          <div className="px-4">
            <SettingRow label="Font scale" description="Adjust UI text size">
              <select
                value={settings.fontScale}
                onChange={(e) => updateSettings({ fontScale: parseFloat(e.target.value) })}
                className="h-8 px-2 rounded-fluent border border-border-default bg-[var(--input-bg)] text-body text-text-primary outline-none focus:border-accent cursor-pointer"
              >
                <option value={0.9}>90%</option>
                <option value={1.0}>100%</option>
                <option value={1.1}>110%</option>
                <option value={1.25}>125%</option>
              </select>
            </SettingRow>
          </div>
          <div className="px-4 py-3">
            <p className="text-body text-text-primary mb-2.5">Data</p>
            <div className="flex gap-2">
              <button
                onClick={exportPresets}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-fluent text-body border border-border-default text-text-secondary hover:text-text-primary hover:bg-[var(--nav-hover-bg)] transition-colors cursor-pointer"
              >
                <Download size={14} />
                Export
              </button>
              <button
                onClick={importPresets}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-fluent text-body border border-border-default text-text-secondary hover:text-text-primary hover:bg-[var(--nav-hover-bg)] transition-colors cursor-pointer"
              >
                <Upload size={14} />
                Import
              </button>
              <button
                onClick={resetSettings}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-fluent text-body border border-border-default text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer"
              >
                <RotateCcw size={14} />
                Reset All Settings
              </button>
            </div>
          </div>
        </div>

        {/* Beta Features */}
        <SectionHeader title="Beta Features" />
        <div className="rounded-fluent-lg border border-amber-500/30 overflow-hidden">
          <div className="px-4 py-3 bg-amber-500/5 border-b border-amber-500/20">
            <div className="flex items-start gap-2">
              <FlaskConical size={14} className="text-amber-400 mt-0.5 shrink-0" />
              <p className="text-caption text-text-tertiary">
                Experimental features may be unstable or change without notice. Enable at your own risk.
              </p>
            </div>
          </div>
          <div className="px-4">
            <SettingRow
              label="Edit preset layouts"
              description="Drag monitors in presets and the Displays page to tweak position and size. Known to occasionally misbehave with unusual configurations."
            >
              <Toggle
                checked={settings.enableEditMode}
                onChange={(v) => updateSettings({ enableEditMode: v })}
              />
            </SettingRow>
          </div>
        </div>

        {/* Danger Zone */}
        <SectionHeader title="Danger Zone" />
        <div className="rounded-fluent-lg border border-red-500/30 overflow-hidden">
          <div className="px-4 py-3">
            <div className="flex items-center justify-between">
              <div className="mr-4">
                <p className="text-body text-text-primary">Factory Reset</p>
                <p className="text-caption text-text-tertiary mt-0.5">
                  Delete all presets and reset settings to defaults
                </p>
              </div>
              <button
                onClick={() => setShowFactoryReset(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-fluent text-body bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20 transition-colors cursor-pointer"
              >
                <Trash2 size={14} />
                Factory Reset
              </button>
            </div>
          </div>
        </div>
      </div>

      <ConfirmDialog
        open={showFactoryReset}
        title="Factory Reset"
        message={`This will delete all ${presets.length} preset${presets.length !== 1 ? 's' : ''} and reset all settings to defaults. This cannot be undone.`}
        confirmLabel="Reset Everything"
        danger
        onConfirm={async () => {
          await clearAllPresets();
          await resetSettings();
          setShowFactoryReset(false);
        }}
        onCancel={() => setShowFactoryReset(false)}
      />
    </motion.div>
  );
}
