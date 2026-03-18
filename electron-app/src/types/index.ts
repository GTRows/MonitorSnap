export interface Monitor {
  id: string;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  refreshRate: number;
  rotation: number;
  isPrimary: boolean;
  scaleFactor: number;
  connector?: string;
  nativeWidth?: number;
  nativeHeight?: number;
  colorDepth?: string;
}

export interface Preset {
  id: string;
  name: string;
  hotkey: string | null;
  monitors: Monitor[];
  createdAt: string;
  updatedAt: string;
}

export interface Settings {
  theme: 'light' | 'dark' | 'system';
  startWithWindows: boolean;
  startMinimized: boolean;
  minimizeAfterApply: boolean;
  escToMinimize: boolean;
  notifications: boolean;
  fontScale: number;
}

export type Page = 'presets' | 'displays' | 'settings' | 'about';

declare global {
  interface Window {
    api: {
      getPresets: () => Promise<Preset[]>;
      getCurrentDisplays: () => Promise<Monitor[]>;
      setDisplayTopology: (topology: 'extend' | 'clone' | 'internal' | 'external') => Promise<{ success: boolean; displays?: Monitor[]; error?: string }>;
      applyPreset: (id: string) => Promise<{ success: boolean; error?: string }>;
      testPresetLayout: (id: string, monitors: Monitor[]) => Promise<{ success: boolean; displays?: Monitor[]; error?: string }>;
      testDisplayLayout: (monitors: Monitor[]) => Promise<{ success: boolean; displays?: Monitor[]; error?: string }>;
      savePreset: (data: { name: string }) => Promise<{ success: boolean; id: string }>;
      updatePreset: (id: string, data: Partial<Preset>) => Promise<{ success: boolean }>;
      deletePreset: (id: string) => Promise<{ success: boolean }>;
      renamePreset: (id: string, name: string) => Promise<{ success: boolean }>;
      duplicatePreset: (id: string) => Promise<{ success: boolean; id: string }>;
      setHotkey: (presetId: string, hotkey: string | null) => Promise<{ success: boolean }>;
      getSettings: () => Promise<Settings>;
      updateSettings: (settings: Partial<Settings>) => Promise<{ success: boolean }>;
      getTheme: () => Promise<'dark' | 'light'>;
      updateTrayPresets: (presets: Array<{ id: string; name: string }>) => Promise<{ success: boolean }>;
      openExternal: (url: string) => Promise<void>;
      onThemeChanged: (callback: (theme: 'dark' | 'light') => void) => () => void;
      onApplyPreset: (callback: (presetId: string) => void) => () => void;
      onSaveCurrentConfig: (callback: () => void) => () => void;
    };
  }
}
