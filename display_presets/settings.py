import json
from display_presets.config import get_settings_file
from display_presets.theme import get_system_theme


class Settings:
    def __init__(self):
        self.file = get_settings_file()

        # General Settings
        self.theme_mode = "system"  # "system", "dark", "light"
        self.start_with_windows = False
        self.start_minimized = False
        self.remember_last_preset = True

        # Notification Settings
        self.notify_preset_applied = True
        self.notify_preset_saved = True
        self.notify_preset_deleted = True
        self.notify_preset_renamed = True
        self.notify_hotkey_changed = True
        self.confirm_preset_delete = True
        self.show_error_messages = True  # Always true, not configurable

        # Behavior Settings
        self.minimize_after_apply = False
        self.esc_to_minimize = False

        # Advanced Settings
        self.show_advanced_settings = False
        self.font_size_multiplier = 1.0
        self.window_width = 1100
        self.window_height = 700

        # Internal state (not saved, runtime only)
        self.last_selected_preset = None

        self.load()

    def load(self):
        if self.file.exists():
            try:
                with open(self.file, 'r') as f:
                    data = json.load(f)

                    # General
                    self.theme_mode = data.get('theme_mode', 'system')
                    self.start_with_windows = data.get('start_with_windows', False)
                    self.start_minimized = data.get('start_minimized', False)
                    self.remember_last_preset = data.get('remember_last_preset', True)

                    # Notifications
                    self.notify_preset_applied = data.get('notify_preset_applied', True)
                    self.notify_preset_saved = data.get('notify_preset_saved', True)
                    self.notify_preset_deleted = data.get('notify_preset_deleted', True)
                    self.notify_preset_renamed = data.get('notify_preset_renamed', True)
                    self.notify_hotkey_changed = data.get('notify_hotkey_changed', True)
                    self.confirm_preset_delete = data.get('confirm_preset_delete', True)

                    # Behavior
                    self.minimize_after_apply = data.get('minimize_after_apply', False)
                    self.esc_to_minimize = data.get('esc_to_minimize', False)

                    # Advanced
                    self.show_advanced_settings = data.get('show_advanced_settings', False)
                    self.font_size_multiplier = data.get('font_size_multiplier', 1.0)
                    self.window_width = data.get('window_width', 1100)
                    self.window_height = data.get('window_height', 700)

                    # Runtime state
                    self.last_selected_preset = data.get('last_selected_preset', None)
            except:
                pass

    def save(self):
        with open(self.file, 'w') as f:
            data = {
                # General
                'theme_mode': self.theme_mode,
                'start_with_windows': self.start_with_windows,
                'start_minimized': self.start_minimized,
                'remember_last_preset': self.remember_last_preset,

                # Notifications
                'notify_preset_applied': self.notify_preset_applied,
                'notify_preset_saved': self.notify_preset_saved,
                'notify_preset_deleted': self.notify_preset_deleted,
                'notify_preset_renamed': self.notify_preset_renamed,
                'notify_hotkey_changed': self.notify_hotkey_changed,
                'confirm_preset_delete': self.confirm_preset_delete,

                # Behavior
                'minimize_after_apply': self.minimize_after_apply,
                'esc_to_minimize': self.esc_to_minimize,

                # Advanced
                'show_advanced_settings': self.show_advanced_settings,
                'font_size_multiplier': self.font_size_multiplier,
                'window_width': self.window_width,
                'window_height': self.window_height,

                # Runtime state
                'last_selected_preset': self.last_selected_preset,
            }
            json.dump(data, f, indent=2)

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

    def reset_to_defaults(self):
        """Reset all settings to default values"""
        # General
        self.theme_mode = "system"
        self.start_with_windows = False
        self.start_minimized = False
        self.remember_last_preset = True

        # Notifications
        self.notify_preset_applied = True
        self.notify_preset_saved = True
        self.notify_preset_deleted = True
        self.notify_preset_renamed = True
        self.notify_hotkey_changed = True
        self.confirm_preset_delete = True

        # Behavior
        self.minimize_after_apply = False
        self.esc_to_minimize = False

        # Advanced
        self.show_advanced_settings = False
        self.font_size_multiplier = 1.0
        self.window_width = 1100
        self.window_height = 700

        # Runtime state
        self.last_selected_preset = None

        self.save()

    def export_to_dict(self):
        """Export settings to dictionary for backup"""
        return {
            'theme_mode': self.theme_mode,
            'start_with_windows': self.start_with_windows,
            'start_minimized': self.start_minimized,
            'remember_last_preset': self.remember_last_preset,
            'notify_preset_applied': self.notify_preset_applied,
            'notify_preset_saved': self.notify_preset_saved,
            'notify_preset_deleted': self.notify_preset_deleted,
            'notify_preset_renamed': self.notify_preset_renamed,
            'notify_hotkey_changed': self.notify_hotkey_changed,
            'confirm_preset_delete': self.confirm_preset_delete,
            'minimize_after_apply': self.minimize_after_apply,
            'esc_to_minimize': self.esc_to_minimize,
            'show_advanced_settings': self.show_advanced_settings,
            'font_size_multiplier': self.font_size_multiplier,
            'window_width': self.window_width,
            'window_height': self.window_height,
        }

    def import_from_dict(self, data):
        """Import settings from dictionary"""
        # General
        self.theme_mode = data.get('theme_mode', 'system')
        self.start_with_windows = data.get('start_with_windows', False)
        self.start_minimized = data.get('start_minimized', False)
        self.remember_last_preset = data.get('remember_last_preset', True)

        # Notifications
        self.notify_preset_applied = data.get('notify_preset_applied', True)
        self.notify_preset_saved = data.get('notify_preset_saved', True)
        self.notify_preset_deleted = data.get('notify_preset_deleted', True)
        self.notify_preset_renamed = data.get('notify_preset_renamed', True)
        self.notify_hotkey_changed = data.get('notify_hotkey_changed', True)
        self.confirm_preset_delete = data.get('confirm_preset_delete', True)

        # Behavior
        self.minimize_after_apply = data.get('minimize_after_apply', False)
        self.esc_to_minimize = data.get('esc_to_minimize', False)

        # Advanced
        self.show_advanced_settings = data.get('show_advanced_settings', False)
        self.font_size_multiplier = data.get('font_size_multiplier', 1.0)
        self.window_width = data.get('window_width', 1100)
        self.window_height = data.get('window_height', 700)

        self.save()
