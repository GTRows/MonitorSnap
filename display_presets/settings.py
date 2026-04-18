import json
import os
import winreg
from display_presets.config import get_settings_file


def get_system_theme() -> str:
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        )
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        winreg.CloseKey(key)
        return "light" if value == 1 else "dark"
    except Exception:
        return "dark"


class Settings:
    def __init__(self):
        self.file = get_settings_file()

        self.theme_mode = "system"  # "system", "dark", "light"
        self.start_with_windows = False
        self.start_minimized = False

        self.notify_preset_applied = True

        self.minimize_after_apply = False
        self.esc_to_minimize = False

        self.font_size_multiplier = 1.0
        self.enable_edit_mode = False

        self.load()

    def load(self):
        if not self.file.exists():
            return
        try:
            with open(self.file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return
        self.theme_mode = data.get('theme_mode', self.theme_mode)
        self.start_with_windows = data.get('start_with_windows', self.start_with_windows)
        self.start_minimized = data.get('start_minimized', self.start_minimized)
        self.notify_preset_applied = data.get('notify_preset_applied', self.notify_preset_applied)
        self.minimize_after_apply = data.get('minimize_after_apply', self.minimize_after_apply)
        self.esc_to_minimize = data.get('esc_to_minimize', self.esc_to_minimize)
        self.font_size_multiplier = data.get('font_size_multiplier', self.font_size_multiplier)
        self.enable_edit_mode = data.get('enable_edit_mode', self.enable_edit_mode)

    def save(self):
        data = {
            'theme_mode': self.theme_mode,
            'start_with_windows': self.start_with_windows,
            'start_minimized': self.start_minimized,
            'notify_preset_applied': self.notify_preset_applied,
            'minimize_after_apply': self.minimize_after_apply,
            'esc_to_minimize': self.esc_to_minimize,
            'font_size_multiplier': self.font_size_multiplier,
            'enable_edit_mode': self.enable_edit_mode,
        }
        # Atomic write: write to a temp file, fsync, then rename. Protects
        # against truncated settings.json if the process is killed mid-write.
        self.file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.file.with_suffix(self.file.suffix + '.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.file)

    @property
    def dark_mode(self):
        if self.theme_mode == "system":
            return get_system_theme() == "dark"
        return self.theme_mode == "dark"

    def reset_to_defaults(self):
        """Reset all settings to default values"""
        self.theme_mode = "system"
        self.start_with_windows = False
        self.start_minimized = False
        self.notify_preset_applied = True
        self.minimize_after_apply = False
        self.esc_to_minimize = False
        self.font_size_multiplier = 1.0
        self.enable_edit_mode = False
        self.save()
