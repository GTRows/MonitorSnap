import winreg
from display_presets.config import get_exe_path


REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "DisplayPresets"


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
    except:
        return False


def enable():
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE)
    winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, get_exe_path())
    winreg.CloseKey(key)


def disable():
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_WRITE)
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
