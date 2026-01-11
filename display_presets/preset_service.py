import json
from pathlib import Path
from display_presets.config import get_presets_dir


class PresetService:
    def __init__(self):
        self.dir = get_presets_dir()

    def save(self, name, config, hotkey=None):
        if not name.strip():
            raise ValueError("Name can't be empty")

        data = {
            'config': config,
            'hotkey': hotkey,
            'created_at': __import__('datetime').datetime.now().isoformat()
        }

        path = self._path(name)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load(self, name):
        path = self._path(name)
        if not path.exists():
            raise FileNotFoundError(f"Preset '{name}' not found")

        with open(path, 'r') as f:
            data = json.load(f)
            # Backward compatibility: check if old format
            if 'config' in data:
                return data
            else:
                # Old format: just the config
                return {'config': data, 'hotkey': None, 'created_at': None}

    def get_config(self, name):
        """Get just the display config"""
        data = self.load(name)
        return data['config']

    def get_hotkey(self, name):
        """Get hotkey for preset"""
        data = self.load(name)
        return data.get('hotkey')

    def set_hotkey(self, name, hotkey):
        """Update hotkey for existing preset"""
        data = self.load(name)
        data['hotkey'] = hotkey
        path = self._path(name)
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def list_names(self):
        return sorted([f.stem for f in self.dir.glob("*.json")])

    def delete(self, name):
        path = self._path(name)
        if not path.exists():
            raise FileNotFoundError(f"Preset '{name}' not found")
        path.unlink()

    def rename(self, old_name, new_name):
        if not new_name.strip():
            raise ValueError("Name can't be empty")

        old_path = self._path(old_name)
        new_path = self._path(new_name)

        if not old_path.exists():
            raise FileNotFoundError(f"Preset '{old_name}' not found")
        if new_path.exists():
            raise FileExistsError(f"Preset '{new_name}' already exists")

        old_path.rename(new_path)

    def _path(self, name):
        # sanitize filename
        for c in '<>:"/\\|?*':
            name = name.replace(c, '_')
        return self.dir / f"{name.strip()}.json"
