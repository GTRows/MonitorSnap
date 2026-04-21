# Quality Roadmap

User-reported audit on 2026-04-21: the app feels inconsistent and amateurish.
This document breaks every complaint into concrete phases. Each phase ships
independently. Scope is limited to what the user called out plus the gaps
that audit surfaces; unrelated feature work stays in `ROADMAP.md`.

Success criterion for the whole roadmap: a fresh user can install, reboot,
and use every toggle without noticing any rough edge.

---

## Phase Q1 - Single identity (naming and branding)

Why this is first: every other fix touches strings that the rename invalidates
(registry key names, AppData folder, artifact names). Doing Q1 after any other
phase means redoing those strings.

### Current state (ground truth)

| Layer | Value |
|---|---|
| Repo | `MonitorSnap` |
| Python package | `display_presets` |
| `appId` | `com.displaypresets.app` |
| `productName` | `DisplayPresets` |
| Installer artifact | `DisplayPresets-Setup-<ver>.exe` |
| Portable artifact | `DisplayPresets-Portable-<ver>.exe` |
| MSI artifact | `DisplayPresets-<ver>.msi` |
| Backend binary | `monitorsnap-backend.exe` |
| AppData folder | `%APPDATA%\DisplayPresets\` |
| Run registry key | `DisplayPresets` |
| CLI module | `python -m display_presets` |
| About page title | `MonitorSnap` |
| README title | `MonitorSnap` |

### Q1.1 Decide the canonical name

Pick one. Recommendation: `MonitorSnap` (repo name is the public-facing
entry point; changing it breaks external links; docs already use it).

### Q1.2 Rename user-facing layer

- `productName` → `MonitorSnap`
- Installer artifact → `MonitorSnap-Setup-<ver>.exe`
- Portable artifact → `MonitorSnap-Portable-<ver>.exe`
- MSI artifact → `MonitorSnap-<ver>.msi`
- Zip artifact → `MonitorSnap-<ver>-win.zip`
- `appId` → `com.monitorsnap.app`
- Run registry key (`autostart.APP_NAME`) → `MonitorSnap`
- Electron window title / tray tooltip → `MonitorSnap`
- All user-visible strings (toasts, dialogs, About page) → `MonitorSnap`
- Release workflow upload-artifact names + release body text

### Q1.3 Rename storage layer with migration

- New AppData root: `%APPDATA%\MonitorSnap\`
- One-shot migration on first launch of the renamed version: if old dir
  exists and new one does not, move it. Log the migration. If both exist,
  keep new and leave old untouched (manual intervention required).
- Same for `debug.log` path, `settings.json` path, `presets/` path.

### Q1.4 Internal identifiers (optional)

Python package rename `display_presets` → `monitorsnap` is invasive
(imports everywhere). Defer unless user wants fully consistent internals.
If we do it: plain rename, update `setup.py`, `tests/`, `backend_main.py`,
`__main__.py`, PyInstaller entry, CI workflows, `CLAUDE.md`.

### Q1.5 Icon audit and replacement

- Inventory: `public/icon.ico`, `public/icon.png`, NSIS installer icon,
  MSI icon, tray `tray-icon.png` (+ light/dark variants if shipped),
  About page logo, HTML favicon.
- Ensure one source SVG → regenerate all sizes (16/32/48/64/128/256) via
  `scripts/generate_icons.py`.
- Verify the installed app's taskbar / Start-menu icon matches the
  in-app icon. Different PNG in the tray is OK; the exe icon must match
  the About-page logo.

### Q1.6 Documentation sweep

- `README.md`, `CLAUDE.md`, `ROADMAP.md`, `CONTRIBUTING.md`,
  `SECURITY.md`, issue templates → replace every `DisplayPresets` /
  `display-presets` reference with `MonitorSnap` where it is
  user-facing. Keep Python import paths as-is until Q1.4 decision.

**Acceptance:** `grep -r "DisplayPresets" --include="*.md"` returns only
historical / changelog references. Installing a fresh build shows
`MonitorSnap` everywhere the user looks (Start menu, taskbar, Task
Manager, Add/Remove Programs, About page).

---

## Phase Q2 - First-run install UX

### Q2.1 Auto-launch after install

- Root cause (likely): NSIS `runAfterFinish` not explicitly enabled, or
  the "run now" checkbox is being unchecked by default.
- Fix: add `"runAfterFinish": true` to `build.nsis`. With
  `oneClick: false`, the final wizard page exposes a "Launch MonitorSnap"
  checkbox; ensure it is present and checked by default.
- Verify on a clean VM / fresh user profile. The checkbox behavior
  differs between electron-builder versions.

### Q2.2 Start Menu and Desktop shortcuts

- Confirm NSIS creates Start-menu entry with the correct name and icon.
- Opt-in desktop shortcut via wizard checkbox.
- Uninstaller removes both.

### Q2.3 Post-install sanity

- Log `MonitorSnap installed, version X.Y.Z` once on first launch.
- Detect "first launch" (no `%APPDATA%\MonitorSnap\` yet) and optionally
  show a one-screen welcome panel with "Save your current layout" CTA.
  Zero if we want to keep the app quiet — decision in the phase itself.

### Q2.4 Portable exe data location

Portable builds should keep settings/presets next to the exe, not in
`%APPDATA%`. Otherwise users running two portable copies share state.
- Detect `PORTABLE_EXECUTABLE_DIR` env var electron-builder sets for
  portable builds; use it for `get_app_dir()` when present.
- Document behavior in README.

---

## Phase Q3 - Settings audit (make every toggle do what it says)

Every checkbox in the Settings page needs a test-backed confirmation that
it observably affects the app. The table lists known status; each row that
is not `verified` becomes a fix task.

| Setting | Reads from | Applied by | Status |
|---|---|---|---|
| theme | `settings.theme_mode` | ThemeProvider | verified |
| startWithWindows | autostart | registry Run key | needs Q3.1 |
| startMinimized | main.ts gate | BrowserWindow.show | **broken** (Q3.2) |
| minimizeAfterApply | presetStore | mainWindow.hide | B2.2 done, retest |
| escToMinimize | App.tsx global handler | mainWindow.hide | B2.3 done, retest |
| notifications | notifyPresetApplied | toast gate | B2.4 done, retest |
| fontScale | App.tsx root font-size | CSS rem | B2.1 done, retest |
| enableEditMode | PresetsPage | drag/drop toggle | verify |

### Q3.1 startWithWindows real-path verification

- Test matrix: installed, portable, dev-mode. For each, after enabling
  the toggle, read back `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
  and assert the path points to the exe the user actually runs.
- In dev mode, the registry will point at the electron dist exe, which
  is not what we want. Gate the toggle off in dev or write a placeholder
  with a dev-mode warning.

### Q3.2 startMinimized race fix (REAL BUG)

- Root: `main.ts:341-344` `ready-to-show` handler calls
  `maybeShowInitialWindow()` as soon as the renderer is ready. At this
  point `startHiddenAtLaunch` is still its default `false` because
  `startPythonBackend()` + settings fetch haven't completed yet. Window
  gets shown; the later settings fetch setting `startHiddenAtLaunch = true`
  arrives too late.
- Fix: add a third gate `settingsLoaded`. `maybeShowInitialWindow()`
  must require `readyToShowFired && settingsLoaded`. Set
  `settingsLoaded = true` after the settings-fetch try/catch (both
  success and failure paths), then call `maybeShowInitialWindow()`.
- Write a unit/integration test with a mocked slow backend proving the
  window is never shown when `startMinimized` is true.

### Q3.3 All-toggles E2E smoke

One manual QA pass after Q3.1 and Q3.2: toggle each setting, reboot or
restart the app as relevant, confirm observed behavior. Record findings.
File any deltas as Q3.N tasks.

---

## Phase Q4 - Polish pass (the "amateur" feeling)

### Q4.1 Empty states

- No presets: CTA ("Save your current layout") instead of blank list.
- No displays: explanation + retry button ("Could not read displays").
- Backend-not-ready: a single unified state (not spinner + toast + empty).

### Q4.2 Error surfaces

- Audit every `catch` that currently swallows or toasts a generic
  message. Replace with the actual backend message where available.
- One canonical toast style per category (success / warn / error), with
  consistent durations.

### Q4.3 Tray UX

- Single-click behavior (B1.5 completed — retest).
- Tooltip shows current preset name after apply, not just app name.
- Submenu always reflects current preset list (B1.3 completed — retest).

### Q4.4 Keyboard / accessibility

- Tab order through sidebar → main panel → footer actions.
- `aria-label` on icon-only buttons.
- Focus ring is visible on all interactive elements (currently stripped
  in some components via `outline: none` without replacement).
- Confirm dialog: Enter = confirm, Esc = cancel.

### Q4.5 Visual consistency

- Spacing scale: enforce one unit (4/8/12/16/24/32) across components.
- Typography: heading/body/mono fonts defined once, never inline.
- Icon stroke / size consistency in Lucide imports.
- Light/dark parity: every hard-coded color has a theme token.

---

## Phase Q5 - Code health audit

### Q5.1 Dead / unused code sweep

- Grep for TODO / FIXME / XXX; close or file issues.
- Remove unused IPC handlers, unused preload methods, unused settings
  helpers, commented-out blocks.
- Prune `electron-app/release/builder-debug.yml` if generated (add to
  `.gitignore`).

### Q5.2 IPC handler error consistency

Every `ipcMain.handle` should:
- Catch its own errors and return `{ success: false, error: message }`
  instead of letting the promise reject silently in the renderer.
- Log to main-process console with a consistent prefix.

### Q5.3 Backend log hygiene

- Rotate `debug.log` at ~5 MB.
- Single log format (timestamp, level, module, message).
- Log the app version and install path on startup so user-submitted
  logs are self-describing.

### Q5.4 Tests for Q3 fixes

- Add integration test that simulates slow backend → start-minimized
  gate holds until settings load.
- Add unit test for the autostart registry value content.

---

## Phase Q6 - Release QA checklist

Runbook executed before tagging each release. Shipping QUALITY_ROADMAP
items without this means regressions re-ship.

### Q6.1 Fresh install QA (clean Windows user)

1. Download `MonitorSnap-Setup-<ver>.exe`.
2. Run installer; confirm Start-menu entry + optional desktop shortcut.
3. Accept "Launch MonitorSnap" checkbox. App opens.
4. Save current layout. Apply a preset.
5. Enable "Start with Windows" + "Start minimized". Reboot.
6. After reboot: app is running, tray icon visible, no window shown.
7. Click tray → window appears.

### Q6.2 Upgrade QA

1. Install previous version. Create presets + custom settings.
2. Install new version on top. Launch.
3. Presets + settings preserved (via AppData migration if Q1.3 shipped).

### Q6.3 Portable QA

1. Download portable exe. Run from `Downloads\`.
2. Verify data goes to portable dir (Q2.4), not AppData.
3. Move exe to USB stick; data moves with it.

### Q6.4 Artifact parity

- Installer, MSI, portable, zip all present on the Release page.
- File sizes within expected range.
- Each opens / runs without SmartScreen exotic errors (standard
  "Unknown publisher" is expected; document in README).

---

## Execution order recommendation

Q1 → Q3.2 (bug) → Q2 (install UX) → Q3 (rest of settings) → Q4 (polish) →
Q5 (health) → Q6 (QA runbook, ongoing).

Q1 before anything else: rename-once-rename-done. Q3.2 immediately after
because it is a real regression the user is feeling daily.

## Out of scope

- New features from `ROADMAP.md` (thumbnails, dock mode, folders, etc.).
- Cross-platform support.
- Code signing.
- Telemetry / crash reporting backend.
