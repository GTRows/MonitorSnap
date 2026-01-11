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
    if getattr(sys, 'frozen', False):
        return sys.executable
    return f'{sys.executable} "{os.path.abspath(sys.argv[0])}"'
