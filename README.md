<div align="center">

<img src="assets/icons/icon_128.png" alt="MonitorSnap" width="96" height="96" />

# MonitorSnap

**Save your monitor layout. Restore it in one click.**

One-click display configuration profiles for Windows. Built for KVM users, dock users, and anyone tired of rearranging monitors every time a display plugs in or out.

[![Latest release](https://img.shields.io/github/v/release/GTRows/MonitorSnap?style=flat-square&color=3b82f6)](https://github.com/GTRows/MonitorSnap/releases/latest)
[![Downloads](https://img.shields.io/github/downloads/GTRows/MonitorSnap/total?style=flat-square&color=3b82f6)](https://github.com/GTRows/MonitorSnap/releases)
[![License: MIT](https://img.shields.io/badge/license-MIT-3b82f6.svg?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%2F11-0078d4?style=flat-square)](https://www.microsoft.com/windows)
[![Stars](https://img.shields.io/github/stars/GTRows/MonitorSnap?style=flat-square&color=yellow)](https://github.com/GTRows/MonitorSnap/stargazers)

[Download](#download) - [Features](#features) - [How it works](#how-it-works) - [Build from source](#build-from-source) - [CLI](#cli-usage)

</div>

---

## Why MonitorSnap?

If you use a **KVM switch**, a **laptop dock**, or plug monitors in and out through the day, Windows keeps scrambling your layout. You lose window positions. You have to open Display Settings. You have to drag things around. Again.

MonitorSnap saves a full snapshot of your display configuration — positions, resolutions, refresh rates, rotation, primary display, topology — and puts it back exactly as it was with a single click, a tray menu item, or a global hotkey.

## Screenshots

<div align="center">

<img src="docs/screenshots/presets.png" alt="Presets page" width="720" />

*Presets page — browse, apply, edit, and delete saved layouts.*

<br /><br />

<img src="docs/screenshots/displays.png" alt="Displays page" width="720" />

*Displays page — live view of current monitors with drag-to-edit layout.*

<br /><br />

<img src="docs/screenshots/tray.png" alt="Tray menu" width="360" />

*System tray menu — apply presets without opening the app.*

</div>

> Screenshots not rendering? Drop PNGs into `docs/screenshots/` with the filenames above.

## Features

- **One-click layout switching.** Apply any saved preset from the main window, the system tray, or a global hotkey.
- **Visual layout editor.** See your monitors exactly as Windows does. Drag them to rearrange, then save.
- **Global hotkeys.** Bind any preset to a shortcut (for example `Ctrl+Alt+Shift+1`). Works system-wide, even when the app is minimized.
- **Full state capture.** Positions, resolutions, refresh rates, rotation (landscape / portrait / flipped), primary display, scaling, and topology (extended, cloned, single).
- **Lives in the system tray.** Quiet, out of the way. Double-click to open, right-click for quick-apply.
- **Fluent Design.** Native Windows 11 look — dark, light, or system theme.
- **Portable option.** Single-file executable if you don't want an installer.
- **CLI included.** Script your layouts from PowerShell or batch files.
- **Auto-start with Windows.** Optional. Fully under your control.

## Download

Head to the **[latest release](https://github.com/GTRows/MonitorSnap/releases/latest)** and grab one of:

| File | When to use |
|---|---|
| `MonitorSnap-Setup-<version>.exe` | Standard NSIS installer. Start Menu entry, uninstaller, updates via reinstall. |
| `MonitorSnap-<version>.msi` | Windows Installer package. For enterprise / group policy deployment. |
| `MonitorSnap-Portable-<version>.exe` | Single-file portable build. Runs from a USB stick or any folder, no install. |
| `MonitorSnap-<version>-win.zip` | Pre-built app folder. Extract anywhere and run `MonitorSnap.exe`. No installer, no registry writes. |

**Requirements:** Windows 10 or 11 (x64). No runtime dependencies — the Python backend is bundled inside the app.

## How it works

MonitorSnap reads the full display configuration from Windows via the [CCD API](https://learn.microsoft.com/en-us/windows-hardware/drivers/display/ccd-apis) (`QueryDisplayConfig` / `SetDisplayConfig`) through Python's `ctypes`. It applies configurations in two phases: first the topology (which monitor is connected to which source), then positions and modes. No registry hacks, no third-party drivers.

```
Electron (React + TypeScript)
      |
      | IPC
      v
Python HTTP backend (stdlib only)
      |
      | ctypes
      v
user32.dll - QueryDisplayConfig / SetDisplayConfig
```

On startup, Electron spawns the Python backend on a random free port and proxies all frontend IPC calls to `http://127.0.0.1:{port}`. No network traffic leaves your machine.

## Build from source

Requirements: Windows, **Python 3.10+**, **Node.js 20+**, **Git**.

```bash
git clone https://github.com/GTRows/MonitorSnap.git
cd MonitorSnap
dev.bat
```

`dev.bat` installs npm dependencies, compiles the Electron main process, and launches the app with the Python backend in dev mode.

Manual equivalent:

```bash
cd electron-app
npm install
npm run electron:dev
```

Build the production installer and portable exe:

```bash
cd electron-app
npm run electron:build
# artifacts land in electron-app/release/
```

## CLI usage

Install the Python package once, then drive everything from the terminal:

```bash
pip install -e .
```

```
monitorsnap list                  List all saved presets
monitorsnap current               Show current display configuration
monitorsnap save "Work Setup"     Save current layout
monitorsnap apply "Work Setup"    Restore a layout
monitorsnap rename <old> <new>    Rename a preset
monitorsnap delete <name>         Delete a preset
monitorsnap info <name>           Show preset details
monitorsnap --version             Print version
```

Or, without installing, `python -m display_presets <command>`.

## Data storage

All user data lives in `%APPDATA%\MonitorSnap\`:

- `presets/{uuid}.json` — saved layouts
- `settings.json` — app preferences
- `debug.log` — diagnostic log

## Tech stack

- **Frontend:** Electron, React 19, TypeScript, TailwindCSS, Zustand, Framer Motion, Vite.
- **Backend:** Python 3.10+ (stdlib only — no pip dependencies), ctypes, stdlib `http.server`.
- **Packaging:** electron-builder (NSIS installer + portable).
- **CI:** GitHub Actions — test, typecheck, build, release on every `v*` tag.

## Roadmap

- Auto-update via GitHub Releases
- Localization (English, Turkish, community translations)
- More hotkey coverage and per-preset activation conditions

## Contributing

Contributions welcome. The project uses a simple branch model:

- `main` — stable releases only, always tagged.
- `develop` — integration branch; features merge here first.
- `feature/<name>` — short-lived branches off `develop`.

Before opening a PR, please run:

```bash
cd electron-app
npx tsc --noEmit
npm test
cd ..
python -m pytest tests/
```

## Known limitations

- All monitors referenced by a preset must be physically connected when you apply it. MonitorSnap will tell you which targets are missing if they aren't.
- Docking stations may need a few seconds to stabilize after connect; apply a preset after Windows settles.
- Custom refresh rates set via GPU control panels are not always captured.
- Hardware and driver limits always win.

## License

MIT — see [LICENSE](LICENSE).

---

<div align="center">

If MonitorSnap saved you time, a **star** helps other Windows users find it.

</div>
