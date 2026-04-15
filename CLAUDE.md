# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MonitorSnap is a Windows desktop app for saving and restoring display configurations. The frontend is Electron + React + TypeScript + TailwindCSS. The backend is a Python HTTP server using the Windows Display Configuration API via ctypes. Primary use case: KVM switch users.

## Development Commands

```bash
# Start the full Electron app (recommended)
dev.bat

# Or manually:
cd electron-app
npm install
npm run electron:dev

# CLI only (no GUI)
python -m display_presets list
python -m display_presets apply "Work Setup"

# Start Python backend standalone (used by Electron internally)
python -m display_presets.server

# TypeScript type check
cd electron-app && npx tsc --noEmit

# Python syntax check
python -c "import py_compile; py_compile.compile('display_presets/server.py', doraise=True)"
```

## Architecture

### Entry Flow

Electron `main.ts` spawns `python -m display_presets.server` as a child process. The server picks a free port, prints `READY:{port}` to stdout. Electron proxies all IPC calls to `http://127.0.0.1:{port}/`.

### Backend Modules (display_presets/)

- **server.py**: HTTP server bridging Electron to Python. Routes: `/presets`, `/displays`, `/settings`.
- **display_config.py**: Windows Display Configuration API wrapper (ctypes). `DisplayConfigManager` handles `QueryDisplayConfig` / `SetDisplayConfig`. Two-phase apply: topology first, then positions.
- **store.py**: UUID-based preset CRUD for the Electron UI. Presets in `%APPDATA%\DisplayPresets\presets\`.
- **displays.py**: Normalizes raw display config into frontend-friendly monitor objects.
- **preset_service.py**: Name-based preset CRUD for the CLI.
- **settings.py**: User preferences (theme, autostart, minimize behavior, font scale).
- **autostart.py**: Windows registry manipulation for startup.
- **logger.py**: Centralized logging to `%APPDATA%\DisplayPresets\debug.log`.
- **config.py**: App data paths (`%APPDATA%\DisplayPresets\`).
- **cli.py**: Command-line interface (list, apply, save, delete, rename, current, info).

### Frontend (electron-app/)

- **electron/main.ts**: Main process. Spawns Python backend, creates window, registers IPC handlers, manages tray.
- **electron/preload.ts**: Context bridge exposing typed API to renderer.
- **src/pages/**: PresetsPage, DisplaysPage, SettingsPage, AboutPage.
- **src/components/**: MonitorCanvas (drag-to-edit), Sidebar, HotkeyInput, Toggle, ConfirmDialog, ContextMenu, ToastContainer.
- **src/stores/**: Zustand stores for presets, settings, app state, toasts.

### Data Storage

All user data in `%APPDATA%\DisplayPresets\`:
- `presets/{uuid}.json` - Saved display configurations
- `settings.json` - Application preferences
- `debug.log` - Debug output

## Code Standards

- **Language**: All code, comments, variable names, and identifiers must be in English. No Turkish or other non-English text in source files.
- **No emojis**: Do not use emojis anywhere in code, comments, or responses. Plain text only.
- **Python**: PEP 8, max 100 chars/line, f-strings, type hints on new functions, `snake_case` for variables/functions, `PascalCase` for classes.
- **TypeScript**: Strict mode, functional React components, Zustand for state.
- **CSS**: TailwindCSS utility classes. Theme tokens defined in `tailwind.config.js`.

## Build Notes

Windows-only due to ctypes bindings to `user32.dll` Display Configuration API. The Python backend has zero pip dependencies (stdlib only).

## Release Standards

Every release MUST produce both of the following artifacts, uploaded to the GitHub release:

1. **Installer** — `DisplayPresets-Setup-<version>.exe` (NSIS, per-user, creates Start Menu entry and uninstaller).
2. **Portable** — `DisplayPresets-Portable-<version>.exe` (single-file executable, no install).

Both targets are configured in `electron-app/package.json` under `build.win.target`. Do not remove either target. `.github/workflows/release.yml` uploads everything matching `electron-app/release/*.exe`.

### Release notes

Release notes are generated automatically in the workflow from the git log between the previous tag and the new one. They must include, as section headings:

- **Downloads** — describe Installer vs Portable so users can pick.
- **Requirements** — Windows version, Python 3.10+ on PATH.
- **Changes** — bullet list of commit subjects (merge commits filtered out), followed by a `Full changelog` compare link.

When cutting a release, verify after the workflow finishes that both `.exe` files are attached to the GitHub release and the notes render correctly. If either is missing, investigate the workflow before tagging the next version.

### Version bump checklist

Every version bump touches exactly these three files — keep them in sync:

- `display_presets/__init__.py` (`__version__`)
- `electron-app/package.json` (`version`)
- `electron-app/src/lib/constants.ts` (`APP_VERSION`)
