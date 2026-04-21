import os
import sys
import winreg
from display_presets.config import get_exe_path


REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "MonitorSnap"
LEGACY_APP_NAMES = ("DisplayPresets",)


def _is_packaged() -> bool:
    # Packaged PyInstaller backend, or Electron explicitly pointed at a packaged exe.
    if getattr(sys, 'frozen', False):
        return True
    app_exe = os.environ.get('MONITORSNAP_APP_EXE') or os.environ.get('DISPLAYPRESETS_APP_EXE')
    if not app_exe:
        return False
    name = os.path.basename(app_exe).lower()
    # In dev, Electron's execPath is electron.exe; refuse to register that.
    return name not in ('electron.exe', 'electron')


def is_enabled():
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ)
        try:
            winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except OSError:
        return False


def _remove_legacy_entries(key):
    for name in LEGACY_APP_NAMES:
        try:
            winreg.DeleteValue(key, name)
        except FileNotFoundError:
            pass


def enable():
    if not _is_packaged():
        raise RuntimeError(
            "Autostart can only be enabled from a packaged build of MonitorSnap. "
            "Running from source or a dev Electron shell would register a path "
            "that Windows cannot launch at login."
        )
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE)
    _remove_legacy_entries(key)
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_exe_path())
    winreg.CloseKey(key)


def disable():
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE)
    _remove_legacy_entries(key)
    try:
        winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass
    winreg.CloseKey(key)


def toggle():
    if is_enabled():
        disable()
        return False
    else:
        enable()
        return True
