"""
HTTP server that bridges the Electron frontend to the Python backend.

Electron spawns this module as a child process via:
    python -m display_presets.server

The server picks a free port, writes "READY:{port}" to stdout, then serves
requests until the process is killed.
"""

import json
import sys
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from display_presets.store import PresetStore
from display_presets.displays import get_current_displays
from display_presets.display_config import DisplayConfigManager
from display_presets.settings import Settings
from display_presets import autostart
from display_presets.logger import get_logger

_store = PresetStore()
_settings = Settings()
_log = get_logger('server')


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settings_to_dict(s: Settings) -> dict:
    return {
        'theme': s.theme_mode,
        'startWithWindows': s.start_with_windows,
        'startMinimized': s.start_minimized,
        'minimizeAfterApply': s.minimize_after_apply,
        'escToMinimize': s.esc_to_minimize,
        'notifications': s.notify_preset_applied,
        'fontScale': s.font_size_multiplier,
        'enableEditMode': s.enable_edit_mode,
    }


def _strip_config(preset: dict) -> dict:
    """Return preset without the raw config blob (not needed by frontend)."""
    return {k: v for k, v in preset.items() if k != 'config'}


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

class _Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):  # suppress access logs
        pass

    # -- response helpers ---------------------------------------------------

    def _json(self, data, status: int = 200):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _ok(self):
        self._json({'success': True})

    def _err(self, message: str, status: int = 400):
        self._json({'error': message}, status)

    def _read_body(self) -> dict:
        length = int(self.headers.get('Content-Length', 0))
        if length:
            return json.loads(self.rfile.read(length))
        return {}

    # -- routing ------------------------------------------------------------

    def _route(self, method: str, path: str):
        parts = [p for p in path.strip('/').split('/') if p]

        # GET /health
        if method == 'GET' and parts == ['health']:
            self._json({'status': 'ok'})

        # GET /presets
        elif method == 'GET' and parts == ['presets']:
            presets = [_strip_config(p) for p in _store.list_all()]
            self._json(presets)

        # POST /presets  – capture current Windows state and save as new preset
        elif method == 'POST' and parts == ['presets']:
            body = self._read_body()
            name = body.get('name', '').strip()
            if not name:
                return self._err('name is required')
            try:
                config = DisplayConfigManager().get_current()
                monitors = get_current_displays()
            except Exception as e:
                _log.exception('Failed to capture display state')
                return self._err(f'Failed to capture display state: {e}', 500)
            preset = _store.create(name=name, monitors=monitors, config=config)
            self._json(_strip_config(preset))

        # GET /presets/:id
        elif method == 'GET' and len(parts) == 2 and parts[0] == 'presets':
            preset = _store.get(parts[1])
            if preset is None:
                return self._err('not found', 404)
            self._json(_strip_config(preset))

        # PUT /presets/:id  – update name / hotkey / monitors
        elif method == 'PUT' and len(parts) == 2 and parts[0] == 'presets':
            body = self._read_body()
            existing = _store.get(parts[1])
            if existing is None:
                return self._err('not found', 404)
            updates = {k: body[k] for k in ('name', 'hotkey', 'monitors') if k in body}
            # When monitors are updated, rebuild the raw config to reflect the new
            # topology (position changes, clone/extend groupings).
            if 'monitors' in updates and existing.get('config'):
                try:
                    updates['config'] = DisplayConfigManager().rebuild_config_for_monitors(
                        existing['config'], updates['monitors']
                    )
                except Exception:
                    _log.exception('rebuild_config_for_monitors failed')
            preset = _store.update(parts[1], updates)
            self._json(_strip_config(preset))

        # DELETE /presets/:id
        elif method == 'DELETE' and len(parts) == 2 and parts[0] == 'presets':
            if _store.delete(parts[1]):
                self._ok()
            else:
                self._err('not found', 404)

        # POST /presets/:id/apply
        elif method == 'POST' and len(parts) == 3 and parts[0] == 'presets' and parts[2] == 'apply':
            preset = _store.get(parts[1])
            if preset is None:
                return self._err('not found', 404)
            config = preset.get('config')
            if not config:
                return self._err('preset has no captured display configuration')
            try:
                _log.info('Applying preset id=%s name=%r', parts[1], preset.get('name'))
                result = DisplayConfigManager().apply(config)
                if result == 0:
                    self._ok()
                else:
                    _log.error('Apply failed: SetDisplayConfig code=%d', result)
                    self._err(f'SetDisplayConfig failed with code {result}', 500)
            except Exception as e:
                _log.exception('Apply raised exception')
                self._err(str(e), 500)

        # POST /presets/:id/test  { monitors: [...] }
        elif method == 'POST' and len(parts) == 3 and parts[0] == 'presets' and parts[2] == 'test':
            preset = _store.get(parts[1])
            if preset is None:
                return self._err('not found', 404)
            config = preset.get('config')
            if not config:
                return self._err('preset has no captured display configuration')
            body = self._read_body()
            monitors = body.get('monitors')
            if not monitors or not isinstance(monitors, list):
                return self._err('monitors array required')
            try:
                mgr = DisplayConfigManager()
                rebuilt = mgr.rebuild_config_for_monitors(config, monitors)
                result = mgr.apply(rebuilt)
                if result == 0:
                    self._json(get_current_displays())
                else:
                    self._err(f'SetDisplayConfig failed with code {result}', 500)
            except Exception as e:
                _log.exception('Test preset layout failed')
                self._err(str(e), 500)

        # POST /presets/:id/duplicate
        elif method == 'POST' and len(parts) == 3 and parts[0] == 'presets' and parts[2] == 'duplicate':
            copy = _store.duplicate(parts[1])
            if copy is None:
                return self._err('not found', 404)
            self._json(_strip_config(copy))

        # PATCH /presets/:id/name
        elif method == 'PATCH' and len(parts) == 3 and parts[0] == 'presets' and parts[2] == 'name':
            body = self._read_body()
            name = body.get('name', '').strip()
            if not name:
                return self._err('name is required')
            preset = _store.update(parts[1], {'name': name})
            if preset is None:
                return self._err('not found', 404)
            self._json(_strip_config(preset))

        # PATCH /presets/:id/hotkey
        elif method == 'PATCH' and len(parts) == 3 and parts[0] == 'presets' and parts[2] == 'hotkey':
            body = self._read_body()
            preset = _store.update(parts[1], {'hotkey': body.get('hotkey')})
            if preset is None:
                return self._err('not found', 404)
            self._json(_strip_config(preset))

        # GET /displays/current
        elif method == 'GET' and parts == ['displays', 'current']:
            try:
                self._json(get_current_displays())
            except Exception as e:
                self._err(str(e), 500)

        # POST /displays/set-topology  { topology: 'extend'|'clone'|'internal'|'external' }
        elif method == 'POST' and parts == ['displays', 'set-topology']:
            body = self._read_body()
            topology = body.get('topology', '').strip()
            if topology not in ('extend', 'clone', 'internal', 'external'):
                return self._err('topology must be extend, clone, internal, or external')
            try:
                DisplayConfigManager().set_topology(topology)
                self._json(get_current_displays())
            except Exception as e:
                self._err(str(e), 500)

        # POST /displays/test-layout  { monitors: [...] }
        elif method == 'POST' and parts == ['displays', 'test-layout']:
            body = self._read_body()
            monitors = body.get('monitors')
            if not monitors or not isinstance(monitors, list):
                return self._err('monitors array required')
            try:
                mgr = DisplayConfigManager()
                config = mgr.get_current()
                rebuilt = mgr.rebuild_config_for_monitors(config, monitors)
                result = mgr.apply(rebuilt)
                if result == 0:
                    self._json(get_current_displays())
                else:
                    self._err(f'SetDisplayConfig failed with code {result}', 500)
            except Exception as e:
                _log.exception('Test display layout failed')
                self._err(str(e), 500)

        # GET /settings
        elif method == 'GET' and parts == ['settings']:
            self._json(_settings_to_dict(_settings))

        # PUT /settings
        elif method == 'PUT' and parts == ['settings']:
            body = self._read_body()
            if 'theme' in body:
                _settings.theme_mode = body['theme']
            if 'startWithWindows' in body:
                _settings.start_with_windows = body['startWithWindows']
                if body['startWithWindows']:
                    autostart.enable()
                else:
                    autostart.disable()
            if 'startMinimized' in body:
                _settings.start_minimized = body['startMinimized']
            if 'minimizeAfterApply' in body:
                _settings.minimize_after_apply = body['minimizeAfterApply']
            if 'escToMinimize' in body:
                _settings.esc_to_minimize = body['escToMinimize']
            if 'notifications' in body:
                _settings.notify_preset_applied = body['notifications']
            if 'fontScale' in body:
                _settings.font_size_multiplier = body['fontScale']
            if 'enableEditMode' in body:
                _settings.enable_edit_mode = body['enableEditMode']
            _settings.save()
            self._json(_settings_to_dict(_settings))

        else:
            self._err('not found', 404)

    def do_GET(self):
        self._route('GET', urlparse(self.path).path)

    def do_POST(self):
        self._route('POST', urlparse(self.path).path)

    def do_PUT(self):
        self._route('PUT', urlparse(self.path).path)

    def do_DELETE(self):
        self._route('DELETE', urlparse(self.path).path)

    def do_PATCH(self):
        self._route('PATCH', urlparse(self.path).path)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    server = HTTPServer(('127.0.0.1', 0), _Handler)
    port = server.server_address[1]
    # Signal to Electron that the server is ready
    print(f'READY:{port}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
