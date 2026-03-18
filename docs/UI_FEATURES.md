# UI Features

## Main Window

### Preset List
- Show all saved presets
- Select a preset (updates preview and hotkey field)
- Remember last selected preset across sessions (optional)
- Double-click a preset to apply it immediately

### Preset Actions
- **New** — save current display configuration as a named preset
- **Apply** — apply the selected preset to the displays
- **Rename** — rename the selected preset
- **Duplicate** — copy the selected preset under a new name
- **Delete** — delete the selected preset (with optional confirmation dialog)

### Monitor Preview
- Visual canvas showing the monitor arrangement for the selected preset
- Each monitor shows: display number, resolution, whether it is primary
- Duplicate/clone mode is visually distinct from extended mode

### Edit Layout Mode
- Toggle edit mode on the preview
- Drag monitors to rearrange positions
- Snap to edges of adjacent monitors
- Snap to exact overlap position (duplicate/clone mode)
- Double-click a monitor to set it as primary
- **Save Layout** — overwrite the current preset with the modified layout
- **Save as New Preset** — save the modified layout as a separate preset
- **Test** — apply the modified layout to the displays temporarily without saving
- **Reset** — revert the preview back to the original positions

### Hotkey Assignment
- Input field to type a hotkey combination for the selected preset
- Save the hotkey; it activates globally even when the window is closed
- Remove a hotkey by clearing the field

---

## Settings

### Appearance
- Theme: System / Dark / Light

### Startup
- Start with Windows (registry autostart)
- Start minimized to tray (skip opening main window on launch)

### Presets
- Remember last selected preset

### Notifications
- Show notification when preset is applied
- Show notification when preset is saved
- Show notification when preset is renamed
- Show notification when preset is deleted
- Show notification when hotkey is assigned or removed
- Ask for confirmation before deleting a preset

### Behavior
- Minimize window after applying a preset
- Press ESC to minimize window to tray

### Advanced
- Font size multiplier (0.8x – 1.5x)
- Default window size (width x height)
- Export settings to JSON file
- Import settings from JSON file
- Reset all settings to defaults (presets are not affected)

---

## System Tray

- Tray icon always visible while app is running
- Double-click icon to open main window
- Right-click context menu:
  - Open main window
  - Save current display configuration as preset (prompts for name)
  - Presets submenu — each saved preset has: Apply, Rename, Delete
  - Exit

---

## Global Hotkeys
- Each preset can have one global hotkey (Ctrl/Alt/Shift + key)
- Hotkeys work in the background even when the window is hidden
- Applying via hotkey does not show a dialog (silent apply)

---

## About
- App name and version
- Usage instructions (save, restore, manage)
- What gets saved (positions, resolutions, refresh rates, orientation, primary, topology)
- Technical details (API names, data folder path)
- Known limitations
- License info
