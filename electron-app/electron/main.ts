import { app, BrowserWindow, ipcMain, Tray, Menu, nativeImage, nativeTheme, shell, globalShortcut } from 'electron';
import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import { toAccelerator } from './hotkey';

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let pythonProcess: ChildProcess | null = null;
let backendPort: number | null = null;

interface BackendStatus {
  ready: boolean;
  error: string | null;
}
let backendStatus: BackendStatus = { ready: false, error: null };

function setBackendStatus(next: BackendStatus): void {
  backendStatus = next;
  mainWindow?.webContents.send('backend-status-changed', next);
}

const isDev = !app.isPackaged;

const GITHUB_OWNER = 'GTRows';
const GITHUB_REPO_NAME = 'MonitorSnap';
const LATEST_RELEASE_URL = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO_NAME}/releases/latest`;

interface UpdateInfo {
  available: boolean;
  currentVersion: string;
  latestVersion: string | null;
  releaseUrl: string | null;
  releaseNotes: string | null;
  publishedAt: string | null;
  checkedAt: string;
  error: string | null;
}

let lastUpdateInfo: UpdateInfo | null = null;

function parseVersion(raw: string): number[] {
  return raw.replace(/^v/i, '').split(/[.+-]/).map((n) => {
    const parsed = parseInt(n, 10);
    return Number.isNaN(parsed) ? 0 : parsed;
  });
}

function isNewerVersion(latest: string, current: string): boolean {
  const a = parseVersion(latest);
  const b = parseVersion(current);
  const len = Math.max(a.length, b.length);
  for (let i = 0; i < len; i++) {
    const x = a[i] ?? 0;
    const y = b[i] ?? 0;
    if (x !== y) return x > y;
  }
  return false;
}

async function fetchLatestRelease(): Promise<UpdateInfo> {
  const current = app.getVersion();
  const base: UpdateInfo = {
    available: false,
    currentVersion: current,
    latestVersion: null,
    releaseUrl: null,
    releaseNotes: null,
    publishedAt: null,
    checkedAt: new Date().toISOString(),
    error: null,
  };
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 10000);
    const res = await fetch(LATEST_RELEASE_URL, {
      headers: {
        Accept: 'application/vnd.github+json',
        'User-Agent': `${GITHUB_REPO_NAME}/${current}`,
      },
      signal: controller.signal,
    });
    clearTimeout(timer);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json() as {
      tag_name: string;
      html_url: string;
      body?: string;
      published_at?: string;
      prerelease?: boolean;
      draft?: boolean;
    };
    if (data.draft || data.prerelease) return base;
    const latest = data.tag_name.replace(/^v/i, '');
    return {
      ...base,
      available: isNewerVersion(latest, current),
      latestVersion: latest,
      releaseUrl: data.html_url,
      releaseNotes: data.body ?? '',
      publishedAt: data.published_at ?? null,
    };
  } catch (err) {
    return {
      ...base,
      error: err instanceof Error ? err.message : String(err),
    };
  }
}

async function runUpdateCheck(notifyIfAvailable: boolean): Promise<UpdateInfo> {
  const info = await fetchLatestRelease();
  lastUpdateInfo = info;
  if (notifyIfAvailable && info.available) {
    mainWindow?.webContents.send('update-available', info);
  }
  return info;
}

// ---------------------------------------------------------------------------
// Python backend
// ---------------------------------------------------------------------------

interface BackendCommand {
  command: string;
  args: string[];
  cwd: string;
}

function resolveBackendCommand(): BackendCommand {
  // Packaged: run the bundled PyInstaller exe shipped in resources/backend/.
  if (app.isPackaged) {
    const exe = path.join(process.resourcesPath, 'backend', 'monitorsnap-backend.exe');
    return { command: exe, args: [], cwd: process.resourcesPath };
  }

  // Dev override: let users point at a specific interpreter.
  if (process.env.DISPLAYPRESETS_PYTHON) {
    return {
      command: process.env.DISPLAYPRESETS_PYTHON,
      args: ['-m', 'display_presets.server'],
      cwd: path.join(__dirname, '../../'),
    };
  }

  // Dev default: use system python + the source package.
  const py = process.platform === 'win32' ? 'python' : 'python3';
  return {
    command: py,
    args: ['-m', 'display_presets.server'],
    cwd: path.join(__dirname, '../../'),
  };
}

function startPythonBackend(): Promise<number> {
  return new Promise((resolve, reject) => {
    const { command, args, cwd } = resolveBackendCommand();
    let stderrBuffer = '';

    const proc = spawn(command, args, {
      cwd,
      env: { ...process.env, DISPLAYPRESETS_APP_EXE: process.execPath },
      windowsHide: true,
    });

    pythonProcess = proc;

    proc.stdout?.on('data', (data: Buffer) => {
      const text = data.toString();
      const match = text.match(/READY:(\d+)/);
      if (match) {
        backendPort = parseInt(match[1], 10);
        resolve(backendPort);
      }
    });

    proc.stderr?.on('data', (data: Buffer) => {
      const text = data.toString();
      stderrBuffer += text;
      console.error('[python]', text.trimEnd());
    });

    proc.on('error', (err) => {
      console.error('Failed to start backend:', err);
      reject(new Error(`${err.message} (tried '${command}' in ${cwd})`));
    });

    proc.on('exit', (code) => {
      console.log(`Python backend exited (code ${code})`);
      pythonProcess = null;
      backendPort = null;
      if (backendPort === null && code !== 0 && code !== null) {
        const snippet = stderrBuffer.trim().split('\n').slice(-5).join('\n');
        reject(new Error(`Python backend exited with code ${code}.\n${snippet}`));
      }
    });

    setTimeout(() => {
      if (backendPort === null) {
        reject(new Error(`Python backend startup timed out after 15s (cwd: ${cwd})`));
      }
    }, 15000);
  });
}

async function api(urlPath: string, options: RequestInit = {}): Promise<unknown> {
  if (!backendPort) throw new Error('Backend not ready');
  const res = await fetch(`http://127.0.0.1:${backendPort}${urlPath}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  const body = await res.json();
  if (!res.ok) throw new Error((body as { error?: string }).error ?? `HTTP ${res.status}`);
  return body;
}

function apiPost(urlPath: string, data?: unknown) {
  return api(urlPath, { method: 'POST', body: data ? JSON.stringify(data) : undefined });
}

function apiPut(urlPath: string, data: unknown) {
  return api(urlPath, { method: 'PUT', body: JSON.stringify(data) });
}

function apiPatch(urlPath: string, data: unknown) {
  return api(urlPath, { method: 'PATCH', body: JSON.stringify(data) });
}

function apiDelete(urlPath: string) {
  return api(urlPath, { method: 'DELETE' });
}

// ---------------------------------------------------------------------------
// Global hotkeys
// ---------------------------------------------------------------------------

type HotkeyStatus = 'ok' | 'unsupported' | 'busy';
let hotkeyStatuses: Record<string, HotkeyStatus> = {};

function setHotkeyStatuses(next: Record<string, HotkeyStatus>): void {
  hotkeyStatuses = next;
  mainWindow?.webContents.send('hotkey-statuses-changed', next);
}

async function registerAllHotkeys(): Promise<void> {
  globalShortcut.unregisterAll();
  const statuses: Record<string, HotkeyStatus> = {};
  try {
    const presets = await api('/presets') as Array<{ id: string; hotkey: string | null; name: string }>;
    for (const p of presets) {
      if (!p.hotkey) continue;
      const accel = toAccelerator(p.hotkey);
      if (!accel) {
        statuses[p.id] = 'unsupported';
        console.warn(`[hotkey] Cannot register "${p.hotkey}" for preset "${p.name}": unsupported key`);
        continue;
      }
      const ok = globalShortcut.register(accel, () => {
        apiPost(`/presets/${p.id}/apply`).catch((e) => console.error('[hotkey] apply failed:', e));
      });
      if (!ok) {
        statuses[p.id] = 'busy';
        console.warn(`[hotkey] Failed to register "${accel}" for preset "${p.name}" (may be taken by another app)`);
      } else {
        statuses[p.id] = 'ok';
      }
    }
  } catch (e) {
    console.error('[hotkey] Could not load presets for registration:', e);
  }
  setHotkeyStatuses(statuses);
}

// ---------------------------------------------------------------------------
// Window
// ---------------------------------------------------------------------------

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1080,
    height: 720,
    minWidth: 860,
    minHeight: 600,
    frame: false,
    titleBarStyle: 'hidden',
    titleBarOverlay: {
      color: nativeTheme.shouldUseDarkColors ? '#1c1c1c' : '#f5f5f5',
      symbolColor: nativeTheme.shouldUseDarkColors ? '#ffffff' : '#1a1a1a',
      height: 40,
    },
    backgroundColor: nativeTheme.shouldUseDarkColors ? '#1c1c1c' : '#f5f5f5',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
    show: false,
    icon: path.join(__dirname, '../public/icon.ico'),
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  mainWindow.on('close', (event) => {
    event.preventDefault();
    mainWindow?.hide();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ---------------------------------------------------------------------------
// Tray
// ---------------------------------------------------------------------------

function createTray(): void {
  const iconPath = path.join(__dirname, '../public/tray-icon.png');
  const icon = nativeImage.createFromPath(iconPath);
  tray = new Tray(icon);
  tray.setToolTip('DisplayPresets');
  updateTrayMenu([]);
  tray.on('double-click', () => {
    mainWindow?.show();
    mainWindow?.focus();
  });
}

function updateTrayMenu(presets: Array<{ id: string; name: string }>): void {
  const presetItems: Electron.MenuItemConstructorOptions[] = presets.map((p) => ({
    label: p.name,
    click: () => {
      mainWindow?.webContents.send('apply-preset', p.id);
    },
  }));

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Open DisplayPresets',
      click: () => { mainWindow?.show(); mainWindow?.focus(); },
    },
    { type: 'separator' },
    ...(presetItems.length > 0
      ? [
          { label: 'Quick Apply', submenu: presetItems } as Electron.MenuItemConstructorOptions,
          { type: 'separator' as const },
        ]
      : []),
    {
      label: 'Save Current Config',
      click: () => {
        mainWindow?.webContents.send('save-current-config');
        mainWindow?.show();
      },
    },
    { type: 'separator' },
    {
      label: 'Exit',
      click: () => {
        mainWindow?.destroy();
        app.quit();
      },
    },
  ]);

  tray?.setContextMenu(contextMenu);
}

// ---------------------------------------------------------------------------
// IPC handlers
// ---------------------------------------------------------------------------

function registerIpcHandlers(): void {
  ipcMain.handle('get-presets', async () => {
    try { return await api('/presets'); }
    catch { return []; }
  });

  ipcMain.handle('get-current-displays', async () => {
    try { return await api('/displays/current'); }
    catch { return []; }
  });

  ipcMain.handle('set-display-topology', async (_event, topology: string) => {
    try {
      const displays = await apiPost('/displays/set-topology', { topology });
      return { success: true, displays };
    } catch (e) {
      return { success: false, error: String(e) };
    }
  });

  ipcMain.handle('apply-preset', async (_event, presetId: string) => {
    try {
      await apiPost(`/presets/${presetId}/apply`);
      return { success: true };
    } catch (e) {
      return { success: false, error: String(e) };
    }
  });

  ipcMain.handle('test-preset-layout', async (_event, presetId: string, monitors: unknown) => {
    try {
      const displays = await apiPost(`/presets/${presetId}/test`, { monitors });
      return { success: true, displays };
    } catch (e) {
      return { success: false, error: String(e) };
    }
  });

  ipcMain.handle('test-display-layout', async (_event, monitors: unknown) => {
    try {
      const displays = await apiPost('/displays/test-layout', { monitors });
      return { success: true, displays };
    } catch (e) {
      return { success: false, error: String(e) };
    }
  });

  ipcMain.handle('save-preset', async (_event, preset: { name: string }) => {
    try {
      const result = await apiPost('/presets', preset) as { id: string };
      return { success: true, id: result.id };
    } catch (e) {
      return { success: false, error: String(e) };
    }
  });

  ipcMain.handle('update-preset', async (_event, presetId: string, data: unknown) => {
    try {
      await apiPut(`/presets/${presetId}`, data);
      await registerAllHotkeys();
      return { success: true };
    } catch (e) {
      return { success: false, error: String(e) };
    }
  });

  ipcMain.handle('delete-preset', async (_event, presetId: string) => {
    try {
      await apiDelete(`/presets/${presetId}`);
      await registerAllHotkeys();
      return { success: true };
    } catch (e) {
      return { success: false, error: String(e) };
    }
  });

  ipcMain.handle('rename-preset', async (_event, presetId: string, newName: string) => {
    try {
      await apiPatch(`/presets/${presetId}/name`, { name: newName });
      return { success: true };
    } catch (e) {
      return { success: false, error: String(e) };
    }
  });

  ipcMain.handle('duplicate-preset', async (_event, presetId: string) => {
    try {
      const result = await apiPost(`/presets/${presetId}/duplicate`) as { id: string };
      return { success: true, id: result.id };
    } catch (e) {
      return { success: false, error: String(e) };
    }
  });

  ipcMain.handle('set-hotkey', async (_event, presetId: string, hotkey: string | null) => {
    try {
      await apiPatch(`/presets/${presetId}/hotkey`, { hotkey });
      await registerAllHotkeys();
      return { success: true };
    } catch (e) {
      return { success: false, error: String(e) };
    }
  });

  ipcMain.handle('get-settings', async () => {
    try { return await api('/settings'); }
    catch {
      return {
        theme: 'system',
        startWithWindows: false,
        startMinimized: false,
        minimizeAfterApply: true,
        escToMinimize: true,
        notifications: true,
        fontScale: 1.0,
      };
    }
  });

  ipcMain.handle('update-settings', async (_event, settings: unknown) => {
    try {
      await apiPut('/settings', settings);
      return { success: true };
    } catch (e) {
      return { success: false, error: String(e) };
    }
  });

  ipcMain.handle('get-theme', () => {
    return nativeTheme.shouldUseDarkColors ? 'dark' : 'light';
  });

  ipcMain.handle('update-tray-presets', async (_event, presets: Array<{ id: string; name: string }>) => {
    updateTrayMenu(presets);
    return { success: true };
  });

  ipcMain.handle('open-external', async (_event, url: string) => {
    await shell.openExternal(url);
  });

  ipcMain.handle('get-backend-status', () => backendStatus);

  ipcMain.handle('check-for-updates', async () => {
    return runUpdateCheck(false);
  });

  ipcMain.handle('get-last-update-info', () => lastUpdateInfo);

  ipcMain.handle('get-hotkey-statuses', () => hotkeyStatuses);

  ipcMain.handle('restart-backend', async () => {
    if (pythonProcess) {
      pythonProcess.kill();
      pythonProcess = null;
    }
    backendPort = null;
    setBackendStatus({ ready: false, error: null });
    try {
      await startPythonBackend();
      setBackendStatus({ ready: true, error: null });
      await registerAllHotkeys();
      return { success: true };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setBackendStatus({ ready: false, error: message });
      return { success: false, error: message };
    }
  });
}

// ---------------------------------------------------------------------------
// App lifecycle
// ---------------------------------------------------------------------------

app.whenReady().then(async () => {
  registerIpcHandlers();
  createWindow();
  createTray();

  try {
    await startPythonBackend();
    console.log(`Python backend ready on port ${backendPort}`);
    setBackendStatus({ ready: true, error: null });
    await registerAllHotkeys();
  } catch (err) {
    console.error('Python backend failed to start:', err);
    setBackendStatus({
      ready: false,
      error: err instanceof Error ? err.message : String(err),
    });
  }

  setTimeout(() => {
    runUpdateCheck(true).catch((e) => console.error('[update-check]', e));
  }, 8000);
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) createWindow();
});

app.on('before-quit', () => {
  globalShortcut.unregisterAll();
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;
  }
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

nativeTheme.on('updated', () => {
  mainWindow?.webContents.send(
    'theme-changed',
    nativeTheme.shouldUseDarkColors ? 'dark' : 'light'
  );
  if (mainWindow) {
    mainWindow.setTitleBarOverlay({
      color: nativeTheme.shouldUseDarkColors ? '#1c1c1c' : '#f5f5f5',
      symbolColor: nativeTheme.shouldUseDarkColors ? '#ffffff' : '#1a1a1a',
    });
  }
});
