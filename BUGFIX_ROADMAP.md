# Bugfix Roadmap

Prioritized list of real bugs found by code audit on 2026-04-18. Each entry
lists the root cause (file:line), user-visible symptom, and fix sketch. Phases
ship independently, B1 first.

## Phase B1 - Tray and hotkey core (blockers)

### B1.1 Tray "Quick Apply" only works on Presets page

- Root: `electron-app/electron/main.ts:340` — tray click sends IPC
  `apply-preset` to the renderer. Only `PresetsPage.tsx:322` listens. When the
  user is on Settings / Displays / About, clicking the tray item does nothing.
- Fix: call `apiPost('/presets/${id}/apply')` directly from the tray click
  handler (same path the hotkey handler uses at `main.ts:258`). Drop the IPC
  detour. Surface apply errors via a main-process `Notification` or backend
  log — do not require the window.
- Also add `api.getCurrentDisplays()` refresh broadcast so any visible page
  re-renders after a tray-triggered apply.

### B1.2 Tray "Save Current Config" requires window

- Root: `main.ts:359` sends `save-current-config` IPC; only PresetsPage
  reacts, by opening its inline input. From tray, nothing happens unless
  PresetsPage is the current page.
- Fix: when handler fires, main process shows+focuses the window AND
  navigates the renderer to Presets before triggering the prompt. Or build a
  small native input dialog in the main process.

### B1.3 Tray menu becomes stale after preset mutations

- Root: IPC handlers `save-preset` (L427), `update-preset` (L436),
  `delete-preset` (L446), `rename-preset` (L456), `duplicate-preset` (L465),
  `set-hotkey` (L474) do not call `updateTrayMenu`. The menu only refreshes
  when the renderer calls `update-tray-presets`, which means rename/delete
  done from the UI updates the tray, but anything that bypasses the usual
  flow (future CLI, direct backend POST, etc.) leaves the tray wrong.
- Fix: after every mutation in main.ts, fetch presets and call
  `updateTrayMenu` directly. Remove the `update-tray-presets` IPC — make the
  main process the single source of truth for tray content.

### B1.4 Tray is created before backend is ready

- Root: `main.ts:558` `createTray()` runs synchronously before
  `await startPythonBackend()` at L561. Initial `updateTrayMenu([])` shows an
  empty Quick Apply submenu. Items appear only when the renderer later pushes
  `update-tray-presets`.
- Fix: move `createTray()` after `startPythonBackend()` succeeds, then call
  `updateTrayMenu(await api('/presets'))` once.

### B1.5 Tray has no single-click behavior

- Root: `main.ts:330` only binds `double-click`. Windows users expect
  single-click to toggle the window.
- Fix: add `tray.on('click', ...)` that toggles window visibility.

### B1.6 Hotkey registration race on every update

- Root: `registerAllHotkeys` at `main.ts:245` unconditionally calls
  `globalShortcut.unregisterAll()` before re-registering all presets. During
  this window every hotkey is unbound. Not a permanent failure, but a
  briefly-pressed hotkey right after saving a new one is eaten.
- Fix: compute diff between currently registered and desired set; unregister
  only removed ones and register only new ones. Keep existing bindings alive.

### B1.7 F-key / single-key hotkeys rejected

- Root: `electron-app/src/lib/hotkey.ts:39` returns null if combo has fewer
  than 2 parts. `electron-app/electron/hotkey.ts:6` does the same. Pressing
  `F12` alone never saves — the input never calls `onChange`.
- Fix: allow F1-F24 and Media/Volume/Play keys as standalone accelerators
  (Electron supports them). Keep the minimum-modifiers rule only for letter/
  digit/punctuation keys.

## Phase B2 - Settings that silently do nothing

Users toggle these in Settings, the server saves them, but no code in the
Electron main or renderer consumes the value. The toggle state persists but
has zero effect.

### B2.1 `fontScale`

- Root: `SettingsPage.tsx:135` writes to backend, but nothing reads it. No
  `--font-scale` CSS variable, no `document.documentElement.style.fontSize`,
  no root Tailwind scale binding.
- Fix: in `App.tsx`, subscribe to settings and set
  `document.documentElement.style.fontSize = ${16 * fontScale}px` on change.
  Base all typography on `rem`.

### B2.2 `minimizeAfterApply`

- Root: `presetStore.applyPreset` (`presetStore.ts:95-109`) never hides the
  window. Toast fires and that's it.
- Fix: add `api.hideWindow()` to preload + IPC handler; call from
  `applyPreset` when `settings.minimizeAfterApply`. Also call from the tray
  click in B1.1 under the same setting.

### B2.3 `escToMinimize`

- Root: `PresetsPage.tsx:332-364` keyboard handler handles Escape only
  inside edit mode (line 340). No global Escape handler in `App.tsx`.
- Fix: add window-level Escape listener in `App.tsx` that hides the window
  when setting is on AND no modal, input, or edit mode is active.

### B2.4 `notifications`

- Root: `presetStore.applyPreset` always calls `toast.success`. No setting
  check. Same in `updatePreset`, `saveCurrentAsPreset`, etc.
- Fix: introduce a `notify()` helper in `toastStore.ts` that reads
  `settingsStore.getState().settings.notifications` and no-ops when false.
  Replace direct `toast.success` calls in preset actions with `notify.success`.

### B2.5 `startMinimized`

- Root: `settings.py:26` stores it, `server.py:267` sets it, but
  `electron-app/electron/main.ts:277-298` always calls
  `mainWindow.once('ready-to-show', () => mainWindow?.show())` without
  checking the setting.
- Fix: read settings from backend after startPythonBackend; skip `.show()`
  when `startMinimized` is true. Start with tray only.

### B2.6 `startWithWindows` error handling

- Root: `autostart.py:23-26, 29-35` open the registry with `KEY_WRITE` and
  write without try/except. Failures bubble up uncaught and the server
  returns a generic 500; the user sees "Failed to update settings" with no
  detail.
- Fix: wrap `enable`/`disable` in try/except, return structured error from
  `server.py:261-266`, show real message in the renderer toast.

## Phase B3 - Data integrity

### B3.1 Import loses data on restart

- Root: `presetStore.importPresets` (`presetStore.ts:275-310`) merges into
  the in-memory `presets` array without ever calling `api.savePreset` /
  `api.updatePreset`. Restart the app and all imported presets are gone. Tray
  also not updated.
- Fix: for each valid imported preset, call `api.savePreset` with
  name+monitors+config (needs a new endpoint that accepts raw
  `monitors`+`config`, not just a name from current displays). Then
  `fetchPresets` and let main rebuild tray (B1.3).

### B3.2 Bulk clear is N round-trips

- Root: `presetStore.clearAllPresets` (`presetStore.ts:319-320`) loops
  `await api.deletePreset` N times.
- Fix: add `DELETE /presets` or `POST /presets/clear` backend endpoint; one
  call; single tray rebuild.

### B3.3 Settings write is not atomic

- Root: `settings.py:94-95` opens `settings.json` in `w` mode and json-dumps
  directly. A crash mid-write leaves the file truncated; next `load` falls
  back to silent defaults (`except (json.JSONDecodeError, OSError): pass` at
  line 91).
- Fix: write to `settings.json.tmp`, fsync, `os.replace(tmp, final)`.

### B3.4 Writes assume parent dir exists

- Root: `config.py:11` creates `%APPDATA%\DisplayPresets` at import time,
  but after that `settings.save` and `store` writes don't re-check. If the
  user deletes the folder while the app is running, writes crash.
- Fix: in each write path, `parent.mkdir(parents=True, exist_ok=True)` right
  before opening the file.

### B3.5 Missing monitor-identity stability

- Root: presets store monitor records with `id` / `name` from the Windows
  enumeration at save time. If Windows re-enumerates in a different order
  (USB replug, driver change), `rebuild_config_for_monitors` may map the
  wrong monitor or fail. Silent failure for users.
- Fix: capture a stable key (EDID serial / device path) alongside id+name.
  Match on EDID first, fall back to name, fall back to position.

## Phase B4 - UX polish

### B4.1 Backend-status events missed during startup

- Root: `main.ts:17-20` `setBackendStatus` sends to `mainWindow` even if
  renderer hasn't finished loading. Events fired during startup are lost.
- Fix: keep a last-status cache (already exists as `backendStatus`); when
  renderer calls `get-backend-status` it sees current state. Also replay
  last status on new window attach (once `did-finish-load` fires).

### B4.2 Hotkey status map leaks stale entries

- Root: `registerAllHotkeys` builds `statuses` fresh each call but only
  adds entries for presets with a hotkey (`main.ts:249-265`). A preset that
  previously had a 'busy' status but got its hotkey cleared still shows the
  old status until the renderer refetches.
- Fix: include every preset id in the map with `null` / omit status
  explicitly; renderer treats "missing" as "no hotkey".

### B4.3 Update-check failures hidden

- Root: `main.ts:102-107` catches fetch errors and stores them on
  `UpdateInfo.error`, but the About page / banner surface only checks
  `.available`.
- Fix: show the error in the About-page update card when present.

### B4.4 Tray icon doesn't follow OS theme

- Root: `main.ts:325-326` loads a single `tray-icon.png`. On dark-mode
  taskbars a light-on-dark icon may be invisible; on light taskbars a
  dark-on-light icon may clash.
- Fix: ship `tray-icon-light.png` and `tray-icon-dark.png`; swap on
  `nativeTheme.on('updated')`.

### B4.5 Dead settings keys

- Root: `settings.py` persists `notify_preset_saved`, `notify_preset_deleted`,
  `notify_preset_renamed`, `notify_hotkey_changed`, `confirm_preset_delete`,
  `remember_last_preset`, `window_width`, `window_height`,
  `show_advanced_settings`, `last_selected_preset` — none exposed to
  frontend, none read at runtime.
- Fix: remove unused keys (breaking change for power users editing JSON,
  document in release notes) OR expose the ones that have clear value
  (confirm_preset_delete, remember_last_preset).

## Phase B5 - Regression tests

Each of the above fixes needs a test to prevent relapse. Prioritize:

- **B5.1** Tray click applies correct preset when main window is hidden
  (integration test with spawned Electron + mock backend).
- **B5.2** Hotkey press applies correct preset after sequential save /
  rename / hotkey-change cycles.
- **B5.3** Each settings toggle has an observable effect (snapshot test:
  `fontScale` changes root font-size; `minimizeAfterApply` calls
  `window.hide`; `escToMinimize` hides on Escape; `notifications` suppresses
  toasts; `startMinimized` skips initial show).
- **B5.4** Import → restart → presets still present.
- **B5.5** `display_config.apply` round-trip with EDID-stable matching
  works after simulated monitor re-enumeration.

## Out of scope for this roadmap

- Anything in the existing `ROADMAP.md` (feature work).
- Windows Display Configuration API edge cases that only bite on unusual
  hardware — track those as issues, not roadmap phases.
- Cross-platform — see main roadmap.
