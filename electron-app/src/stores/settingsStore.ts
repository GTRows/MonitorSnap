import { create } from 'zustand';
import type { Settings } from '@/types';
import { toast } from '@/stores/toastStore';

const api = window.api;
const useMock = !api;

interface SettingsState {
  settings: Settings;
  resolvedTheme: 'dark' | 'light';
  loading: boolean;

  fetchSettings: () => Promise<void>;
  updateSettings: (partial: Partial<Settings>) => Promise<void>;
  resetSettings: () => Promise<void>;
  setResolvedTheme: (theme: 'dark' | 'light') => void;
}

const defaultSettings: Settings = {
  theme: 'system',
  startWithWindows: false,
  startMinimized: false,
  minimizeAfterApply: true,
  escToMinimize: true,
  notifications: true,
  fontScale: 1.0,
  enableEditMode: false,
};

export const useSettingsStore = create<SettingsState>((set, get) => ({
  settings: defaultSettings,
  resolvedTheme: 'dark',
  loading: false,

  fetchSettings: async () => {
    set({ loading: true });
    if (useMock) {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      set({ settings: defaultSettings, resolvedTheme: prefersDark ? 'dark' : 'light', loading: false });
      return;
    }
    const [settings, systemTheme] = await Promise.all([
      api.getSettings(),
      api.getTheme(),
    ]);
    const resolvedTheme = settings.theme === 'system' ? systemTheme : settings.theme;
    set({ settings, resolvedTheme, loading: false });
  },

  updateSettings: async (partial) => {
    const previousSettings = get().settings;
    const newSettings = { ...previousSettings, ...partial };
    set({ settings: newSettings });

    if (partial.theme) {
      if (partial.theme === 'system') {
        if (useMock) {
          const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
          set({ resolvedTheme: prefersDark ? 'dark' : 'light' });
        } else {
          const systemTheme = await api.getTheme();
          set({ resolvedTheme: systemTheme });
        }
      } else {
        set({ resolvedTheme: partial.theme });
      }
    }

    if (!useMock) {
      const result = await api.updateSettings(newSettings);
      if (!result.success) {
        set({ settings: result.settings ?? previousSettings });
        toast.error(result.error ?? 'Failed to update settings');
      } else if (result.settings) {
        set({ settings: result.settings });
      }
    }
  },

  resetSettings: async () => {
    set({ settings: defaultSettings });
    const resolvedTheme = defaultSettings.theme === 'system'
      ? (useMock
          ? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light')
          : await api.getTheme())
      : defaultSettings.theme;
    set({ resolvedTheme });
    if (!useMock) {
      await api.updateSettings(defaultSettings);
    }
  },

  setResolvedTheme: (theme) => set({ resolvedTheme: theme }),
}));
