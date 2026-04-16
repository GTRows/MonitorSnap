import { contextBridge, ipcRenderer } from 'electron';

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

const api = {
  getPresets: (): Promise<Preset[]> => ipcRenderer.invoke('get-presets'),
  getCurrentDisplays: (): Promise<Monitor[]> => ipcRenderer.invoke('get-current-displays'),
  setDisplayTopology: (topology: 'extend' | 'clone' | 'internal' | 'external'): Promise<{ success: boolean; displays?: Monitor[]; error?: string }> => ipcRenderer.invoke('set-display-topology', topology),
  applyPreset: (id: string): Promise<{ success: boolean; error?: string }> => ipcRenderer.invoke('apply-preset', id),
  testPresetLayout: (id: string, monitors: Monitor[]): Promise<{ success: boolean; displays?: Monitor[]; error?: string }> => ipcRenderer.invoke('test-preset-layout', id, monitors),
  testDisplayLayout: (monitors: Monitor[]): Promise<{ success: boolean; displays?: Monitor[]; error?: string }> => ipcRenderer.invoke('test-display-layout', monitors),
  savePreset: (data: { name: string }): Promise<{ success: boolean; id: string }> => ipcRenderer.invoke('save-preset', data),
  updatePreset: (id: string, data: Partial<Preset>): Promise<{ success: boolean }> => ipcRenderer.invoke('update-preset', id, data),
  deletePreset: (id: string): Promise<{ success: boolean }> => ipcRenderer.invoke('delete-preset', id),
  renamePreset: (id: string, name: string): Promise<{ success: boolean }> => ipcRenderer.invoke('rename-preset', id, name),
  duplicatePreset: (id: string): Promise<{ success: boolean; id: string }> => ipcRenderer.invoke('duplicate-preset', id),
  setHotkey: (presetId: string, hotkey: string | null): Promise<{ success: boolean }> => ipcRenderer.invoke('set-hotkey', presetId, hotkey),
  getSettings: (): Promise<Settings> => ipcRenderer.invoke('get-settings'),
  updateSettings: (settings: Partial<Settings>): Promise<{ success: boolean }> => ipcRenderer.invoke('update-settings', settings),
  getTheme: (): Promise<'dark' | 'light'> => ipcRenderer.invoke('get-theme'),
  updateTrayPresets: (presets: Array<{ id: string; name: string }>): Promise<{ success: boolean }> => ipcRenderer.invoke('update-tray-presets', presets),
  openExternal: (url: string): Promise<void> => ipcRenderer.invoke('open-external', url),
  getBackendStatus: (): Promise<{ ready: boolean; error: string | null }> => ipcRenderer.invoke('get-backend-status'),
  restartBackend: (): Promise<{ success: boolean; error?: string }> => ipcRenderer.invoke('restart-backend'),
  checkForUpdates: (): Promise<UpdateInfo> => ipcRenderer.invoke('check-for-updates'),
  getLastUpdateInfo: (): Promise<UpdateInfo | null> => ipcRenderer.invoke('get-last-update-info'),

  onUpdateAvailable: (callback: (info: UpdateInfo) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, info: UpdateInfo) => callback(info);
    ipcRenderer.on('update-available', handler);
    return () => ipcRenderer.removeListener('update-available', handler);
  },

  getHotkeyStatuses: (): Promise<HotkeyStatusMap> => ipcRenderer.invoke('get-hotkey-statuses'),

  onHotkeyStatusesChanged: (callback: (statuses: HotkeyStatusMap) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, statuses: HotkeyStatusMap) => callback(statuses);
    ipcRenderer.on('hotkey-statuses-changed', handler);
    return () => ipcRenderer.removeListener('hotkey-statuses-changed', handler);
  },

  onBackendStatusChanged: (callback: (status: { ready: boolean; error: string | null }) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, status: { ready: boolean; error: string | null }) => callback(status);
    ipcRenderer.on('backend-status-changed', handler);
    return () => ipcRenderer.removeListener('backend-status-changed', handler);
  },

  onThemeChanged: (callback: (theme: 'dark' | 'light') => void) => {
    const handler = (_event: Electron.IpcRendererEvent, theme: 'dark' | 'light') => callback(theme);
    ipcRenderer.on('theme-changed', handler);
    return () => ipcRenderer.removeListener('theme-changed', handler);
  },

  onApplyPreset: (callback: (presetId: string) => void) => {
    const handler = (_event: Electron.IpcRendererEvent, presetId: string) => callback(presetId);
    ipcRenderer.on('apply-preset', handler);
    return () => ipcRenderer.removeListener('apply-preset', handler);
  },

  onSaveCurrentConfig: (callback: () => void) => {
    const handler = () => callback();
    ipcRenderer.on('save-current-config', handler);
    return () => ipcRenderer.removeListener('save-current-config', handler);
  },
};

contextBridge.exposeInMainWorld('api', api);
