import subprocess
import sys
import os
from pathlib import Path

def build():
    print("Building MonitorSnap.exe...")

    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Get paths
    project_root = Path(__file__).parent.parent
    icon_path = project_root / "assets" / "icons" / "app.ico"

    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=MonitorSnap",
        f"--icon={icon_path}",
        "--add-data", f"{project_root / 'assets' / 'icons'};assets/icons",
        "--hidden-import=display_presets.config",
        "--hidden-import=display_presets.theme",
        "--hidden-import=display_presets.display_config",
        "--hidden-import=display_presets.preset_service",
        "--hidden-import=display_presets.settings",
        "--hidden-import=display_presets.hotkey_manager",
        "--hidden-import=display_presets.autostart",
        "--hidden-import=display_presets.gui",
        "--hidden-import=display_presets.tray",
        str(project_root / "display_presets" / "__main__.py")
    ]

    subprocess.check_call(cmd)
    print("\nDone! Check dist\\MonitorSnap.exe")

if __name__ == "__main__":
    build()
