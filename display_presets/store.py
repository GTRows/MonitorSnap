import json
import uuid
import datetime
from display_presets.config import get_presets_dir


class PresetStore:
    """UUID-based preset store. Each preset is a JSON file named {id}.json."""

    def __init__(self):
        self.dir = get_presets_dir()

    def list_all(self):
        presets = []
        for f in self.dir.glob("*.json"):
            # Skip files that look like old name-based presets (no UUID pattern)
            try:
                uuid.UUID(f.stem)
            except ValueError:
                continue
            try:
                with open(f, encoding='utf-8') as fp:
                    data = json.load(fp)
                if 'id' in data and 'name' in data:
                    presets.append(data)
            except Exception:
                pass
        return sorted(presets, key=lambda p: p.get('created_at', ''))

    def get(self, preset_id):
        path = self.dir / f"{preset_id}.json"
        if not path.exists():
            return None
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None

    def create(self, name, monitors, config=None, hotkey=None):
        preset_id = str(uuid.uuid4())
        now = datetime.datetime.now().isoformat()
        preset = {
            'id': preset_id,
            'name': name,
            'hotkey': hotkey,
            'monitors': monitors,
            'config': config,
            'createdAt': now,
            'updatedAt': now,
        }
        self._write(preset_id, preset)
        return preset

    def update(self, preset_id, updates):
        preset = self.get(preset_id)
        if preset is None:
            return None
        # Only update allowed fields
        for key in ('name', 'hotkey', 'monitors', 'config'):
            if key in updates:
                preset[key] = updates[key]
        preset['updatedAt'] = datetime.datetime.now().isoformat()
        self._write(preset_id, preset)
        return preset

    def delete(self, preset_id):
        path = self.dir / f"{preset_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def duplicate(self, preset_id):
        preset = self.get(preset_id)
        if preset is None:
            return None
        return self.create(
            name=f"{preset['name']} (Copy)",
            monitors=preset.get('monitors', []),
            config=preset.get('config'),
            hotkey=None,
        )

    def _write(self, preset_id, data):
        path = self.dir / f"{preset_id}.json"
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
