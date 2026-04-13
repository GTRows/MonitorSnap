# MonitorSnap

A Windows desktop app for saving and restoring display configurations. Built with Electron + React frontend and a Python backend using the Windows Display Configuration API.

Primary use case: KVM switch users who need to instantly switch between different display setups.

## Features

- Save and restore complete display configurations
- Visual monitor layout preview with drag-to-rearrange editing
- System tray with quick-apply menu
- Dark / Light / System theme (Windows 11 Fluent Design)
- Auto-start with Windows
- Export / Import presets
- CLI interface for scripting

## What Gets Saved

Each preset captures the full display state via Windows Display Configuration API:

- Monitor positions (X, Y coordinates)
- Resolutions and refresh rates
- Orientation (landscape, portrait, flipped)
- Primary monitor assignment
- Display topology (extended, cloned, single)
- Scaling settings

## Installation

### From Source

Requirements: Windows 11, Python 3.10+, Node.js 20+

```bash
git clone https://github.com/GTRows/MonitorSnap.git
cd MonitorSnap

# Start the Electron app (handles everything)
dev.bat
```

`dev.bat` installs npm dependencies, builds the Electron main process, and launches the app with the Python backend.

### Manual Start

```bash
cd electron-app
npm install
npm run electron:dev
```

This starts Vite dev server + Electron. The Python HTTP backend is spawned automatically by the Electron main process.

### CLI Only (no GUI)

```bash
pip install -e .
monitorsnap list
monitorsnap save "Work Setup"
monitorsnap apply "Work Setup"
```

## Architecture

```
Electron Main Process
    |
    |-- spawns --> Python HTTP Server (127.0.0.1:{random port})
    |                  |
    |                  |-- display_config.py  (Windows CCD API via ctypes)
    |                  |-- store.py           (preset CRUD, %APPDATA%)
    |                  |-- settings.py        (user preferences)
    |                  |-- displays.py        (current monitor info)
    |
    |-- IPC --> React Renderer (Vite + TailwindCSS + Zustand)
                   |
                   |-- pages/      (Presets, Displays, Settings, About)
                   |-- components/ (MonitorCanvas, HotkeyInput, etc.)
                   |-- stores/     (presetStore, settingsStore, etc.)
```

The Python server picks a free port, writes `READY:{port}` to stdout. Electron reads this and proxies all IPC requests to `http://127.0.0.1:{port}/`.

## Project Structure

```
MonitorSnap/
  display_presets/             Python backend
    __main__.py                CLI entry point
    server.py                  HTTP server for Electron
    display_config.py          Windows Display Configuration API (ctypes)
    displays.py                Current monitor info
    store.py                   UUID-based preset CRUD
    preset_service.py          Name-based preset CRUD (CLI)
    settings.py                User preferences
    config.py                  App data paths
    autostart.py               Windows registry startup
    logger.py                  File + stderr logging
    cli.py                     CLI commands

  electron-app/                Electron + React frontend
    electron/
      main.ts                  Main process, spawns Python backend
      preload.ts               Context bridge (typed IPC API)
    src/
      pages/                   PresetsPage, DisplaysPage, SettingsPage, AboutPage
      components/              MonitorCanvas, MonitorEditPanel, Sidebar, HotkeyInput,
                               Toggle, ConfirmDialog, ContextMenu, Tooltip, Toast
      stores/                  Zustand (presets, settings, app, toast)
      lib/                     Utilities (openLink, constants)
      types/                   TypeScript type definitions

  assets/icons/                Source icon files
  scripts/                     Icon generation (generate_icons.py)
  docs/                        UI feature spec
  .github/workflows/           CI/CD (build + release)
```

## Data Storage

All user data in `%APPDATA%\DisplayPresets\`:

- `presets/{uuid}.json` -- saved display configurations
- `settings.json` -- app preferences
- `debug.log` -- debug output

## CLI Usage

```
python -m display_presets <command>

Commands:
  list                  List all saved presets
  apply <name>          Apply a preset
  save <name>           Save current display config
  delete <name>         Delete a preset
  rename <old> <new>    Rename a preset
  current               Show current display info
  info <name>           Show preset details
  --version             Show version
```

## Branch Strategy

```
main                Stable releases only. Every commit is tagged (v2.0.0, v2.1.0, ...).
 \
  develop           Integration branch. Tested features land here first.
   \
    feature/xxx     Short-lived branches for individual features or fixes.
```

### Rules

- **`main`** -- Production. Only receives merges from `develop` when cutting a release. Always tagged.
- **`develop`** -- Staging area. All feature work merges here after testing. Must stay buildable.
- **`feature/*`** -- Created from `develop`, merged back into `develop` via PR. Deleted after merge.

### Workflow

```bash
# Start a new feature
git checkout develop
git pull origin develop
git checkout -b feature/my-feature

# Work, commit, push
git push -u origin feature/my-feature

# When done: open PR into develop, review, merge, delete branch.
# When releasing: merge develop into main, tag, push.
```

### Hotfix

For urgent fixes on a released version:

```bash
git checkout main
git checkout -b hotfix/fix-description
# fix, commit, PR into main AND develop
```

## Roadmap

Planned features for upcoming releases:

- **Auto-update** -- Check for new versions on startup, download and install updates automatically via GitHub Releases
- **Localization** -- Multi-language UI support (English, Turkish, and community translations)
- **Tests** -- Unit and integration tests for both Python backend (pytest) and Electron frontend

## Known Issues

- All monitors from the preset must be physically connected when applying
- Laptop docking stations may need a few seconds to stabilize before applying
- Custom refresh rates set via GPU control panel may not be captured
- Cannot override hardware or driver limitations

## License

MIT -- see [LICENSE](LICENSE)
