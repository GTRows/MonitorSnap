import json
import os
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

    def delete_all(self):
        deleted = 0
        for f in self.dir.glob("*.json"):
            try:
                uuid.UUID(f.stem)
            except ValueError:
                continue
            try:
                f.unlink()
                deleted += 1
            except OSError:
                pass
        return deleted

    def import_many(self, presets):
        """Import a list of preset dicts. Returns (imported_count, skipped_count).
        Preserves the incoming id if it is a valid UUID and writes the file
        directly; invalid or missing ids get a freshly generated UUID. Any
        existing file with the same id is overwritten. Imported presets keep
        their monitors but start without a raw display config; the user must
        re-capture the layout on this machine before they can be applied."""
        imported = 0
        skipped = 0
        now = datetime.datetime.now().isoformat()
        for p in presets:
            if not isinstance(p, dict):
                skipped += 1
                continue
            name = p.get('name')
            monitors = p.get('monitors')
            if not isinstance(name, str) or not name.strip() or not isinstance(monitors, list):
                skipped += 1
                continue
            hotkey = p.get('hotkey') if isinstance(p.get('hotkey'), str) else None
            preset_id = p.get('id') if isinstance(p.get('id'), str) else None
            if preset_id:
                try:
                    uuid.UUID(preset_id)
                except ValueError:
                    preset_id = None
            if not preset_id:
                preset_id = str(uuid.uuid4())
            record = {
                'id': preset_id,
                'name': name.strip(),
                'hotkey': hotkey,
                'monitors': monitors,
                'config': None,
                'createdAt': p.get('createdAt') if isinstance(p.get('createdAt'), str) else now,
                'updatedAt': now,
            }
            self._write(preset_id, record)
            imported += 1
        return imported, skipped

    def _write(self, preset_id, data):
        # Ensure the presets directory exists (user may have deleted it at
        # runtime) and write atomically via a temp file + rename.
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self.dir / f"{preset_id}.json"
        tmp = path.with_suffix(path.suffix + '.tmp')
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
