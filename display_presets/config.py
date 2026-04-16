import os
import sys
from pathlib import Path


def get_app_dir():
    if sys.platform == 'win32':
        appdata = os.environ.get('APPDATA')
        if appdata:
            d = Path(appdata) / "DisplayPresets"
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
    app_exe = os.environ.get('DISPLAYPRESETS_APP_EXE')
    if app_exe:
        return f'"{app_exe}"'
    if getattr(sys, 'frozen', False):
        return sys.executable
    return f'{sys.executable} "{os.path.abspath(sys.argv[0])}"'
