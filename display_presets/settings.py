import json
from display_presets.config import get_settings_file
from display_presets.theme import get_system_theme


class Settings:
    def __init__(self):
        self.file = get_settings_file()
        self.theme_mode = "system"  # "system", "dark", "light"
        self.load()

    def load(self):
        if self.file.exists():
            try:
                with open(self.file, 'r') as f:
                    data = json.load(f)
                    self.theme_mode = data.get('theme_mode', 'system')
            except:
                pass

    def save(self):
        with open(self.file, 'w') as f:
            json.dump({'theme_mode': self.theme_mode}, f, indent=2)

    @property
    def dark_mode(self):
        if self.theme_mode == "system":
            return get_system_theme() == "dark"
        return self.theme_mode == "dark"

    def set_theme(self, mode):
        """Set theme: 'system', 'dark', or 'light'"""
        if mode in ["system", "dark", "light"]:
            self.theme_mode = mode
            self.save()

    def toggle_dark_mode(self):
        """Legacy method for compatibility"""
        if self.theme_mode == "dark":
            self.theme_mode = "light"
        else:
            self.theme_mode = "dark"
        self.save()
        return self.dark_mode
