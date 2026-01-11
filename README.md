# Display Presets

A simple tray app to save and restore Windows display configurations. Useful when you frequently switch between different monitor setups.

## Why?

Windows forgets your monitor positions when you disconnect/reconnect displays. This tool saves your exact configuration (positions, resolutions, refresh rates, orientation) and lets you restore it with one click.

## Features

- Save unlimited display presets
- Visual preview of monitor layout
- Restore with one click from tray menu
- Global hotkeys for instant preset switching
- Rename/delete presets
- Dark/Light/System theme
- Auto-start with Windows
- Fully portable (all data in %APPDATA%)

## Installation

### Quick start (Python)

```bash
# Clone the repository
git clone https://github.com/yourusername/DisplayPresets.git
cd DisplayPresets

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m display_presets
```

### Install as package

```bash
pip install -e .
display-presets
```

### Standalone executable

```bash
python scripts/build_exe.py
```

Run `dist\DisplayPresets.exe` - no Python needed.

### Windows installer

1. Build exe (see above)
2. Download [Inno Setup](https://jrsoftware.org/isdl.php)
3. Compile `setup.iss`
4. Install from `installer\DisplayPresetsSetup.exe`

## Usage

### Quick Start

1. **Launch the app** - It runs in the system tray (look for the monitor icon)
2. **Arrange your monitors** - Use Windows Display Settings to set up your ideal configuration
3. **Save as preset**:
   - Right-click tray icon → "Save current preset..."
   - Or double-click tray icon → "New" button
   - Enter a descriptive name (e.g., "Work Setup", "Gaming", "Triple Monitor")
4. **Apply anytime**:
   - Right-click tray icon → Presets → [Your preset] → Apply
   - Or use the hotkey you assigned (see below)

### Example Scenarios

**Laptop + Docking Station Setup:**
```
Preset "Mobile":     Just laptop screen
Preset "Docked":     Laptop + 2 external monitors in specific arrangement
Preset "Presentation": Laptop + projector (duplicate mode)

Hotkeys:
- Ctrl+Shift+1 → Mobile
- Ctrl+Shift+2 → Docked
- Ctrl+Shift+3 → Presentation
```

**Multi-Monitor Gaming Setup:**
```
Preset "Gaming":       Main monitor 144Hz, others off
Preset "Productivity": All monitors at native resolution
Preset "Streaming":    Main monitor + side monitor for OBS

Press Ctrl+Shift+G to instantly switch to gaming mode!
```

### Main Window (Dashboard)

**Double-click** the tray icon to open the dashboard.

**Three tabs:**
- **Presets** - Manage all presets with visual preview
  - Left: List of saved presets (double-click to apply)
  - Right: Visual monitor layout showing positions and Monitor 1, 2, 3...
  - Bottom: Assign hotkeys (e.g., Ctrl+Shift+1) for instant switching
- **Settings** - Theme (Dark/Light/System), autostart, data folder location
- **About** - Version info, usage guide, technical details

### Tray Menu

**Right-click** the tray icon for quick access:
- **Dashboard** - Opens the main window
- **Save current preset...** - Quick save without opening dashboard
- **Presets → [name]** - Apply, Rename, or Delete any preset
- **Exit** - Close the application

### Global Hotkeys

Assign custom hotkeys to each preset for instant switching:
- Format: `Ctrl+Shift+1`, `Ctrl+Alt+F1`, `Ctrl+Shift+M`, etc.
- Hotkeys work globally even when the window is hidden
- Press the hotkey anytime to instantly apply that preset
- Configure in: Dashboard → Select preset → Enter hotkey → Save

## How it works

Uses Windows Display Configuration API:
- `GetDisplayConfigBufferSizes`
- `QueryDisplayConfig`
- `SetDisplayConfig`

Saves raw display paths and modes to JSON, then restores exactly as-is.

## Data storage

Everything lives in `%APPDATA%\DisplayPresets\`:
- `presets\` - Your saved configurations
- `settings.json` - App preferences

Access via **Settings → Open data folder**

## Project Structure

```
DisplayPresets/
├── display_presets/          # Main Python package
│   ├── __init__.py          # Package initialization
│   ├── __main__.py          # Entry point (python -m display_presets)
│   ├── gui.py               # Main window & UI
│   ├── tray.py              # System tray application
│   ├── display_config.py    # Windows Display Configuration API
│   ├── hotkey_manager.py    # Global hotkey handling
│   ├── preset_service.py    # Preset management
│   ├── settings.py          # Application settings
│   ├── config.py            # Configuration & paths
│   ├── autostart.py         # Windows startup integration
│   └── theme.py             # Theme detection
├── assets/
│   └── icons/               # Application icons
│       ├── app.ico
│       └── icon_*.png
├── scripts/                 # Build & utility scripts
│   ├── build_exe.py
│   ├── create_ico.py
│   └── icon_generator.py
├── docs/                    # Documentation
│   ├── BUILD_INSTRUCTIONS.md
│   └── CONTRIBUTING.md
├── tests/                   # Unit tests (future)
├── .gitignore              # Git ignore rules
├── LICENSE                 # MIT License
├── MANIFEST.in             # Package manifest
├── README.md               # This file
├── requirements.txt        # Python dependencies
└── setup.py                # Package setup
```

## Building from source

See [docs/BUILD_INSTRUCTIONS.md](docs/BUILD_INSTRUCTIONS.md)

## Requirements

- Windows 10/11
- Python 3.8+ (for running from source)
- No dependencies for compiled exe

## License

MIT - see [LICENSE](LICENSE)

## Known issues

- Won't work if monitors are disconnected (all monitors from the preset must be connected)
- Some laptop docking stations need a few seconds to stabilize before applying presets
- Cannot override hardware or driver limitations
- Custom refresh rates set via GPU control panel may not be saved

## User Interface

### Main Dashboard
- **Left panel**: List of all saved presets
- **Right panel**: Visual preview showing monitor layout with positions and resolutions
- **Bottom section**: Hotkey assignment for quick access
- **Actions**: New, Apply, Rename, Delete buttons

### System Tray Menu
- **Dashboard**: Opens the main window
- **Save current preset**: Quick save without opening dashboard
- **Presets submenu**: Apply, Rename, or Delete any preset
- **Exit**: Close the application

### Themes
- **Dark mode**: Windows 11 Fluent Design Dark theme
- **Light mode**: Windows 11 Fluent Design Light theme
- **System theme**: Automatically follows Windows theme setting

The UI follows Windows 11 design language with modern colors, typography (Segoe UI Variable), and card-based layouts similar to PowerToys.

## Troubleshooting

**Preset won't apply:**
- Make sure all monitors from the saved preset are currently connected
- Try disconnecting and reconnecting monitors
- Check if Windows Display Settings can manually set the configuration

**Hotkey not working:**
- Make sure the hotkey combination isn't already used by another application
- Try a different key combination (e.g., Ctrl+Shift+F1 instead of Ctrl+Shift+1)
- Check if the application is running in the system tray

**App icon not showing:**
- Make sure `app.ico` exists in the application folder
- Try regenerating icons with `python icon_generator.py` and `python create_ico.py`

## Contributing

Contributions are welcome! This project started as a personal tool and has grown into a full-featured application.

**How to contribute:**
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test thoroughly on Windows 10/11
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

**Ideas for contributions:**
- Support for display rotation in preview
- Export/import presets to share with others
- Command-line interface for scripting
- Display profile auto-switching based on connected monitors
- Integration with Windows Task Scheduler for automatic preset application

## Changelog

### Version 1.0.0 (2026-01)
- Initial public release
- Save and restore display configurations
- Global hotkey support
- Visual monitor preview with sequential numbering
- Dark/Light/System theme support
- Auto-start with Windows
- System tray integration
