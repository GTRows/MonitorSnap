# Build Instructions

## Quick build (Standalone EXE)

```bash
pip install pyinstaller
python build_exe.py
```

Output: `dist\DisplayPresets.exe`

This exe doesn't need Python installed.

## Manual build

```bash
pyinstaller --onefile --windowed --name=DisplayPresets main.py
```

## Windows Installer

Need [Inno Setup](https://jrsoftware.org/isdl.php) installed.

1. Build exe (see above)
2. Open `setup.iss` in Inno Setup Compiler
3. Build → Compile

Output: `installer\DisplayPresetsSetup.exe`

The installer will:
- Install to Program Files
- Add Start Menu shortcut
- Optionally add desktop icon
- Optionally enable auto-start
- Include uninstaller

## Distribution

**Just the exe**: Share `dist\DisplayPresets.exe` - fully portable

**Installer**: Share `installer\DisplayPresetsSetup.exe` - proper Windows installation

## Data location

All user data goes to `%APPDATA%\DisplayPresets\`:
- `presets\*.json` - Saved configurations
- `settings.json` - App settings

## Auto-start

Enable from app: Settings → Start with Windows

This adds a registry entry:
```
HKCU\Software\Microsoft\Windows\CurrentVersion\Run
Name: DisplayPresets
Value: "path\to\DisplayPresets.exe"
```

## Uninstall

**Exe version**:
1. Delete exe file
2. Delete `%APPDATA%\DisplayPresets\` folder
3. Remove from startup if enabled

**Installer version**:
- Use Windows "Add or remove programs"
- Or Start Menu → Display Presets → Uninstall
