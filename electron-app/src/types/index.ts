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
  devicePath?: string | null;
  edidManufactureId?: number;
  edidProductCodeId?: number;
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
  enableEditMode: boolean;
}

export type Page = 'presets' | 'displays' | 'settings' | 'about';

export interface UpdateInfo {
  available: boolean;
  currentVersion: string;
  latestVersion: string | null;
  releaseUrl: string | null;
  releaseNotes: string | null;
  publishedAt: string | null;
  checkedAt: string;
  error: string | null;
}

export type HotkeyStatus = 'ok' | 'unsupported' | 'busy';
export type HotkeyStatusMap = Record<string, HotkeyStatus>;

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
      importPresets: (presets: Preset[]) => Promise<{ success: boolean; imported: number; skipped: number; error?: string }>;
      clearAllPresets: () => Promise<{ success: boolean; deleted: number; error?: string }>;
      setHotkey: (presetId: string, hotkey: string | null) => Promise<{ success: boolean }>;
      getSettings: () => Promise<Settings>;
      updateSettings: (settings: Partial<Settings>) => Promise<{ success: boolean; settings?: Settings; error?: string }>;
      getTheme: () => Promise<'dark' | 'light'>;
      updateTrayPresets: (presets: Array<{ id: string; name: string }>) => Promise<{ success: boolean }>;
      openExternal: (url: string) => Promise<void>;
      getBackendStatus: () => Promise<{ ready: boolean; error: string | null }>;
      hideWindow: () => Promise<void>;
      restartBackend: () => Promise<{ success: boolean; error?: string }>;
      checkForUpdates: () => Promise<UpdateInfo>;
      getLastUpdateInfo: () => Promise<UpdateInfo | null>;
      getHotkeyStatuses: () => Promise<HotkeyStatusMap>;
      onBackendStatusChanged: (callback: (status: { ready: boolean; error: string | null }) => void) => () => void;
      onThemeChanged: (callback: (theme: 'dark' | 'light') => void) => () => void;
      onApplyPreset: (callback: (presetId: string) => void) => () => void;
      onSaveCurrentConfig: (callback: () => void) => () => void;
      onPresetApplied: (callback: (presetId: string) => void) => () => void;
      onUpdateAvailable: (callback: (info: UpdateInfo) => void) => () => void;
      onHotkeyStatusesChanged: (callback: (statuses: HotkeyStatusMap) => void) => () => void;
    };
  }
}
