import pytest

from display_presets import config, preset_service, settings as settings_mod, store


@pytest.fixture
def app_dir(tmp_path, monkeypatch):
    """Redirect app data paths to a temporary directory for the test.

    Modules import get_presets_dir/get_settings_file by name, so we have to
    patch the already-bound references inside each consumer module too.
    """
    presets = tmp_path / "presets"
    presets.mkdir()
    settings_file = tmp_path / "settings.json"

    monkeypatch.setattr(config, "get_app_dir", lambda: tmp_path)
    monkeypatch.setattr(config, "get_presets_dir", lambda: presets)
    monkeypatch.setattr(config, "get_settings_file", lambda: settings_file)

    monkeypatch.setattr(store, "get_presets_dir", lambda: presets)
    monkeypatch.setattr(preset_service, "get_presets_dir", lambda: presets)
    monkeypatch.setattr(settings_mod, "get_settings_file", lambda: settings_file)

    return tmp_path
