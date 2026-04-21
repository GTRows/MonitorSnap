# MonitorSnap Roadmap

Forward-looking plan for work beyond v2.5.0. Phases are grouped by theme and
can ship independently.

## Already shipped (for context)

Core loop (save / apply / delete presets), per-preset hotkeys with
conflict/unsupported/busy feedback, drag-to-edit monitor canvas, four-target
Windows distribution (NSIS + MSI + portable + zip), bundled Python backend
(PyInstaller, no runtime dep), CLI, light/dark/system theme, autostart,
minimize-to-tray, preset import/export, GitHub Releases update check with
in-app banner and About-page card.

## Phase 1 - UI / UX polish

Visible refinements across the app. Individually small, cumulatively the
difference between "functional" and "polished".

- **Preset thumbnail preview.** Render the monitor-canvas layout to a small
  PNG (or live SVG) for each preset. Show on the preset list, hotkey quick
  picker, and tray menu. Cache on disk, invalidate when preset edited.
- **Preset folders / tagging.** Organize presets under user-defined groups
  (`Work`, `Gaming`, `Home`, ...). Sidebar filter, tag-scoped cycling
  hotkeys, drag-to-regroup.
- **Dock mode.** Compact always-on-top mini widget: preset list + apply
  buttons only, frameless, corner-snappable, translucent. Toggle via
  tray or hotkey. Useful during gaming sessions where the full window
  is overkill.
- **Custom accent color.** Replace the fixed accent token with a user-
  selectable hue (preset swatches + free picker). Persist in settings,
  propagate through Tailwind theme variables.

## Phase 2 - Core infrastructure

Quality and contributor-experience work. No user-visible features, but
everything downstream depends on this being solid.

- **Integration test suite.** Real Windows Display Configuration API tests
  (`QueryDisplayConfig` round-trip, topology diffing, path/mode parsing,
  two-phase apply). Runs on `windows-latest` in CI alongside unit tests.
  Target: meaningful coverage on `display_config.py`, `displays.py`,
  `store.py`.
- **Contributor documentation.** `CONTRIBUTING.md` covering local setup,
  branching model (develop -> main), commit style, test expectations,
  how to run the Python backend standalone, how to debug Electron IPC.
  Issue and PR templates. Architecture overview diagram in `docs/`.
- **i18n infrastructure.** `react-i18next` wiring, string-extraction pass
  across all components, seed locales (English, Turkish). Runtime language
  switcher in Settings, `navigator.language` default. Keep translation
  files as plain JSON for PR-based contributions.
- **Crash reporter (local-only).** Catch uncaught exceptions in both the
  Electron main process and the renderer; write a structured crash dump
  (stack, app version, OS build, last preset action) to
  `%APPDATA%\DisplayPresets\crashes\`. Show a "Report crash" button in
  the About page that opens the folder. No network telemetry.

## Phase 3 - Distribution

Make the app easier to find and install via standard Windows package
managers. No binary signing (deferred - cost not justified).

- **winget manifest.** Submit to `microsoft/winget-pkgs`. Enables
  `winget install MonitorSnap`. Automate manifest bump as part of the
  release workflow (or via `winget-create`). Verify install / uninstall /
  upgrade flow against the NSIS installer.

## Out of scope (noted to keep decisions explicit)

- **Code signing.** Authenticode / Azure Trusted Signing / EV certs all
  cost money for a free hobby project. Users clear the SmartScreen prompt
  manually. README should document the bypass path.
- **Cross-platform (macOS / Linux).** MonitorSnap is a thin UI over the
  Windows Display Configuration API; portability would be a rewrite.
- **Cloud sync of presets.** Point the preset directory at a file-sync
  provider (OneDrive / Dropbox) instead; we do not run infra.
- **Auto-apply / smart triggers, wallpaper-per-preset, HDR control,
  Stream Deck, etc.** Previously considered, intentionally deferred.
