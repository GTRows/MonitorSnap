import os
import shutil
import sys
from pathlib import Path

APP_DIR_NAME = "MonitorSnap"
LEGACY_APP_DIR_NAMES = ("DisplayPresets",)


def _migrate_legacy_app_dir(appdata_root: Path, target: Path) -> None:
    if target.exists():
        return
    for legacy_name in LEGACY_APP_DIR_NAMES:
        legacy = appdata_root / legacy_name
        if legacy.exists() and legacy.is_dir():
            try:
                shutil.move(str(legacy), str(target))
            except OSError:
                return
            return


def get_app_dir():
    override = os.environ.get('MONITORSNAP_DATA_DIR')
    if override:
        d = Path(override)
        d.mkdir(parents=True, exist_ok=True)
        return d
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA')
        if appdata:
            root = Path(appdata)
            d = root / APP_DIR_NAME
            _migrate_legacy_app_dir(root, d)
            d.mkdir(exist_ok=True)
            return d
    return Path.cwd()


def get_presets_dir():
    d = get_app_dir() / "presets"
    d.mkdir(exist_ok=True)
    return d


def get_settings_file():
    return get_app_dir() / "settings.json"


def get_exe_path():
    # When the Electron shell spawns the backend it sets this to its own exe
    # path so that "Start with Windows" launches the GUI, not the backend alone.
    app_exe = os.environ.get('MONITORSNAP_APP_EXE') or os.environ.get('DISPLAYPRESETS_APP_EXE')
    if app_exe:
        return f'"{app_exe}"'
    if getattr(sys, 'frozen', False):
        return sys.executable
    return f'{sys.executable} "{os.path.abspath(sys.argv[0])}"'
