import pytest

from display_presets import server
from display_presets.server import _settings_to_dict, _strip_config
from display_presets.settings import Settings
from display_presets.store import PresetStore


def test_settings_to_dict_maps_all_fields():
    s = Settings()
    s.theme_mode = 'dark'
    s.start_with_windows = True
    s.start_minimized = True
    s.minimize_after_apply = False
    s.esc_to_minimize = True
    s.notify_preset_applied = False
    s.font_size_multiplier = 1.25
    s.enable_edit_mode = True

    result = _settings_to_dict(s)

    assert result == {
        'theme': 'dark',
        'startWithWindows': True,
        'startMinimized': True,
        'minimizeAfterApply': False,
        'escToMinimize': True,
        'notifications': False,
        'fontScale': 1.25,
        'enableEditMode': True,
    }


def test_strip_config_removes_config_key():
    preset = {'id': '1', 'name': 'A', 'config': {'paths': []}, 'monitors': []}
    stripped = _strip_config(preset)
    assert 'config' not in stripped
    assert stripped['id'] == '1'
    assert stripped['name'] == 'A'
    assert stripped['monitors'] == []


def test_strip_config_does_not_mutate_input():
    preset = {'id': '1', 'config': {'paths': []}}
    _strip_config(preset)
    assert 'config' in preset


def test_strip_config_passthrough_when_no_config_key():
    preset = {'id': '1', 'name': 'A'}
    assert _strip_config(preset) == preset


@pytest.mark.parametrize("method,suffix", [
    ("GET", ""), ("PUT", ""), ("DELETE", ""),
    ("POST", "/apply"), ("POST", "/test"), ("POST", "/duplicate"),
    ("PATCH", "/name"), ("PATCH", "/hotkey"),
])
def test_preset_routes_reject_windows_traversal(app_dir, monkeypatch, method, suffix):
    store = PresetStore()
    monkeypatch.setattr(server, "_store", store)
    outside = app_dir / "outside.json"
    original = '{"name": "Outside", "monitors": [], "config": {"paths": []}}'
    outside.write_text(original, encoding="utf-8")
    handler = server._Handler.__new__(server._Handler)
    responses = []
    handler._json = lambda data, status=200: responses.append((status, data))
    handler._read_body = lambda: {"name": "Changed", "hotkey": "Ctrl+1"}

    handler._route(method, r"/presets/..\outside" + suffix)

    assert responses == [(404, {"error": "not found"})]
    assert outside.read_text(encoding="utf-8") == original
    assert store.list_all() == []
