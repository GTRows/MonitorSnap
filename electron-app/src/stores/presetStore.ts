import { create } from 'zustand';
import type { Preset, Monitor } from '@/types';
import { toast } from '@/stores/toastStore';
import { useSettingsStore } from '@/stores/settingsStore';

// Mock data for development without Electron
const mockPresets: Preset[] = [
  {
    id: '1',
    name: 'Work Setup',
    hotkey: null,
    monitors: [
      { id: 'm1', name: 'Dell U2723QE', x: 0, y: 0, width: 3840, height: 2160, refreshRate: 60, rotation: 0, isPrimary: true, scaleFactor: 1.5 },
      { id: 'm2', name: 'LG 27UK850', x: 3840, y: 0, width: 3840, height: 2160, refreshRate: 60, rotation: 0, isPrimary: false, scaleFactor: 1.5 },
    ],
    createdAt: '2026-01-15T10:00:00Z',
    updatedAt: '2026-03-10T14:30:00Z',
  },
  {
    id: '2',
    name: 'Gaming',
    hotkey: null,
    monitors: [
      { id: 'm3', name: 'ASUS ROG PG27AQN', x: 0, y: 0, width: 2560, height: 1440, refreshRate: 360, rotation: 0, isPrimary: true, scaleFactor: 1.0 },
    ],
    createdAt: '2026-02-01T08:00:00Z',
    updatedAt: '2026-03-12T20:15:00Z',
  },
  {
    id: '3',
    name: 'Presentation',
    hotkey: null,
    monitors: [
      { id: 'm4', name: 'Laptop Display', x: 0, y: 0, width: 1920, height: 1080, refreshRate: 60, rotation: 0, isPrimary: true, scaleFactor: 1.25 },
      { id: 'm5', name: 'Projector', x: 1920, y: 0, width: 1920, height: 1080, refreshRate: 60, rotation: 0, isPrimary: false, scaleFactor: 1.0 },
    ],
    createdAt: '2026-02-20T12:00:00Z',
    updatedAt: '2026-02-20T12:00:00Z',
  },
];

const mockDisplays: Monitor[] = [
  { id: 'm1', name: 'Dell U2723QE', x: 0, y: 0, width: 3840, height: 2160, refreshRate: 60, rotation: 0, isPrimary: true, scaleFactor: 1.5 },
  { id: 'm2', name: 'LG 27UK850', x: 3840, y: 0, width: 3840, height: 2160, refreshRate: 60, rotation: 0, isPrimary: false, scaleFactor: 1.5 },
];

const api = window.api;
const useMock = !api;

// Shared post-apply side effects: toast + optional window hide. Called from
// both renderer-initiated applyPreset and tray-triggered preset-applied IPC.
export function notifyPresetApplied(presetName: string): void {
  const { notifications, minimizeAfterApply } = useSettingsStore.getState().settings;
  if (notifications) toast.success(`"${presetName}" applied`);
  if (minimizeAfterApply && api) api.hideWindow();
}

interface PresetState {
  presets: Preset[];
  selectedPresetId: string | null;
  currentDisplays: Monitor[];
  loading: boolean;

  fetchPresets: () => Promise<void>;
  fetchCurrentDisplays: () => Promise<void>;
  selectPreset: (id: string | null) => void;
  applyPreset: (id: string) => Promise<boolean>;
  saveCurrentAsPreset: (name: string) => Promise<void>;
  updatePreset: (id: string, data: Partial<Preset>) => Promise<void>;
  deletePreset: (id: string) => Promise<void>;
  renamePreset: (id: string, name: string) => Promise<void>;
  duplicatePreset: (id: string) => Promise<void>;
  setHotkey: (presetId: string, hotkey: string | null) => Promise<void>;
  testPresetLayout: (id: string, monitors: Monitor[]) => Promise<boolean>;
  testDisplayLayout: (monitors: Monitor[]) => Promise<boolean>;
  reorderPresets: (ids: string[]) => void;
  exportPresets: () => void;
  importPresets: () => void;
  clearAllPresets: () => Promise<void>;
}

export const usePresetStore = create<PresetState>((set, get) => ({
  presets: [],
  selectedPresetId: null,
  currentDisplays: [],
  loading: false,

  fetchPresets: async () => {
    set({ loading: true });
    const presets = useMock ? mockPresets : await api.getPresets();
    set({ presets, loading: false });
    if (api) {
      api.updateTrayPresets(presets.map((p) => ({ id: p.id, name: p.name })));
    }
  },

  fetchCurrentDisplays: async () => {
    const displays = useMock ? mockDisplays : await api.getCurrentDisplays();
    set({ currentDisplays: displays });
  },

  selectPreset: (id) => set({ selectedPresetId: id }),

  applyPreset: async (id) => {
    const preset = get().presets.find((p) => p.id === id);
    if (useMock) {
      notifyPresetApplied(preset?.name ?? id);
      return true;
    }
    const result = await api.applyPreset(id);
    if (result.success) {
      await get().fetchCurrentDisplays();
      notifyPresetApplied(preset?.name ?? id);
    } else {
      toast.error(result.error ? `Apply failed: ${result.error}` : 'Failed to apply preset');
    }
    return result.success;
  },

  saveCurrentAsPreset: async (name) => {
    const { currentDisplays } = get();
    if (useMock) {
      const newPreset: Preset = {
        id: Date.now().toString(),
        name,
        hotkey: null,
        monitors: currentDisplays,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      set((state) => ({ presets: [...state.presets, newPreset] }));
      toast.success(`Preset "${name}" saved`);
      return;
    }
    const result = await api.savePreset({ name });
    if (result.success) {
      await Promise.all([get().fetchPresets(), get().fetchCurrentDisplays()]);
      toast.success(`Preset "${name}" saved`);
    } else {
      toast.error('Failed to save preset');
    }
  },

  updatePreset: async (id, data) => {
    if (useMock) {
      set((state) => ({
        presets: state.presets.map((p) =>
          p.id === id ? { ...p, ...data, updatedAt: new Date().toISOString() } : p
        ),
      }));
      toast.success('Preset saved');
      return;
    }
    const result = await api.updatePreset(id, data);
    if (result.success) {
      await get().fetchPresets();
      toast.success('Preset saved');
    } else {
      toast.error('Failed to save preset');
    }
  },

  deletePreset: async (id) => {
    const preset = get().presets.find((p) => p.id === id);
    if (useMock) {
      set((state) => ({
        presets: state.presets.filter((p) => p.id !== id),
        selectedPresetId: state.selectedPresetId === id ? null : state.selectedPresetId,
      }));
      toast.info(`"${preset?.name ?? 'Preset'}" deleted`);
      return;
    }
    const result = await api.deletePreset(id);
    if (result.success) {
      set((state) => ({
        selectedPresetId: state.selectedPresetId === id ? null : state.selectedPresetId,
      }));
      await get().fetchPresets();
      toast.info(`"${preset?.name ?? 'Preset'}" deleted`);
    } else {
      toast.error('Failed to delete preset');
    }
  },

  renamePreset: async (id, name) => {
    if (useMock) {
      set((state) => ({
        presets: state.presets.map((p) => (p.id === id ? { ...p, name, updatedAt: new Date().toISOString() } : p)),
      }));
      toast.success(`Renamed to "${name}"`);
      return;
    }
    const result = await api.renamePreset(id, name);
    if (result.success) {
      await get().fetchPresets();
      toast.success(`Renamed to "${name}"`);
    } else {
      toast.error('Failed to rename preset');
    }
  },

  duplicatePreset: async (id) => {
    const preset = get().presets.find((p) => p.id === id);
    if (!preset) return;

    if (useMock) {
      const copyName = `${preset.name} (Copy)`;
      const newPreset: Preset = {
        ...preset,
        id: Date.now().toString(),
        name: copyName,
        hotkey: null,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      set((state) => ({ presets: [...state.presets, newPreset] }));
      toast.success(`"${copyName}" created`);
      return;
    }
    const result = await api.duplicatePreset(id);
    if (result.success) {
      await get().fetchPresets();
      toast.success(`"${preset.name} (Copy)" created`);
    } else {
      toast.error('Failed to duplicate preset');
    }
  },

  testPresetLayout: async (id, monitors) => {
    if (useMock) {
      toast.info('Mock: test layout applied');
      return true;
    }
    const result = await api.testPresetLayout(id, monitors);
    if (result.success && result.displays) {
      set({ currentDisplays: result.displays as Monitor[] });
      toast.success('Test layout applied');
    } else {
      toast.error(result.error ? `Test failed: ${result.error}` : 'Failed to test layout');
    }
    return result.success;
  },

  testDisplayLayout: async (monitors) => {
    if (useMock) {
      toast.info('Mock: test layout applied');
      return true;
    }
    const result = await api.testDisplayLayout(monitors);
    if (result.success && result.displays) {
      set({ currentDisplays: result.displays as Monitor[] });
      toast.success('Layout applied');
    } else {
      toast.error(result.error ? `Apply failed: ${result.error}` : 'Failed to apply layout');
    }
    return result.success;
  },

  reorderPresets: (ids: string[]) => {
    set((state) => {
      const map = new Map(state.presets.map((p) => [p.id, p]));
      const reordered = ids.map((id) => map.get(id)).filter(Boolean) as Preset[];
      return { presets: reordered };
    });
    if (api) {
      const { presets } = get();
      api.updateTrayPresets(presets.map((p) => ({ id: p.id, name: p.name })));
    }
  },

  exportPresets: () => {
    const { presets } = get();
    const data = JSON.stringify({ version: 1, presets }, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `displaypresets-export-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success(`Exported ${presets.length} preset${presets.length !== 1 ? 's' : ''}`);
  },

  importPresets: () => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = () => {
      const file = input.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = async (e) => {
        let parsed: Preset[];
        try {
          const json = JSON.parse(e.target?.result as string);
          const raw = Array.isArray(json) ? json : json?.presets;
          if (!Array.isArray(raw)) throw new Error('Invalid format');
          parsed = raw.filter((p) => p && typeof p.name === 'string' && Array.isArray(p.monitors));
        } catch {
          toast.error('Import failed: invalid file format');
          return;
        }
        if (parsed.length === 0) {
          toast.error('Import failed: no valid presets found');
          return;
        }
        if (useMock) {
          const { presets } = get();
          const merged = [...presets];
          let added = 0;
          for (const p of parsed) {
            const exists = merged.findIndex((x) => x.id === p.id);
            if (exists >= 0) merged[exists] = p;
            else { merged.push(p); added++; }
          }
          set({ presets: merged });
          toast.success(`Imported ${added} new preset${added !== 1 ? 's' : ''}`);
          return;
        }
        const result = await api.importPresets(parsed);
        if (!result.success) {
          toast.error(result.error ? `Import failed: ${result.error}` : 'Failed to import presets');
          return;
        }
        await get().fetchPresets();
        toast.success(`Imported ${result.imported} preset${result.imported !== 1 ? 's' : ''}`);
      };
      reader.readAsText(file);
    };
    input.click();
  },

  clearAllPresets: async () => {
    const { presets } = get();
    if (useMock) {
      set({ presets: [], selectedPresetId: null });
      toast.success(`Cleared ${presets.length} preset${presets.length !== 1 ? 's' : ''}`);
      return;
    }
    const result = await api.clearAllPresets();
    if (!result.success) {
      toast.error(result.error ? `Clear failed: ${result.error}` : 'Failed to clear presets');
      return;
    }
    set({ presets: [], selectedPresetId: null });
    toast.success(`Cleared ${result.deleted} preset${result.deleted !== 1 ? 's' : ''}`);
  },

  setHotkey: async (presetId, hotkey) => {
    if (useMock) {
      set((state) => ({
        presets: state.presets.map((p) =>
          p.id === presetId ? { ...p, hotkey, updatedAt: new Date().toISOString() } : p
        ),
      }));
      toast.success(hotkey ? 'Hotkey set' : 'Hotkey cleared');
      return;
    }
    const result = await api.setHotkey(presetId, hotkey);
    if (result.success) {
      await get().fetchPresets();
      toast.success(hotkey ? 'Hotkey set' : 'Hotkey cleared');
    } else {
      toast.error('Failed to update hotkey');
    }
  },
}));
