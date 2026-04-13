import json

from display_presets.settings import Settings


def test_defaults_when_no_file(app_dir):
    s = Settings()
    assert s.theme_mode == "system"
    assert s.start_with_windows is False
    assert s.start_minimized is False
    assert s.minimize_after_apply is False
    assert s.esc_to_minimize is False
    assert s.notify_preset_applied is True
    assert s.font_size_multiplier == 1.0
    assert s.enable_edit_mode is False


def test_save_then_load_roundtrip(app_dir):
    s = Settings()
    s.theme_mode = "dark"
    s.start_with_windows = True
    s.font_size_multiplier = 1.25
    s.enable_edit_mode = True
    s.save()

    s2 = Settings()
    assert s2.theme_mode == "dark"
    assert s2.start_with_windows is True
    assert s2.font_size_multiplier == 1.25
    assert s2.enable_edit_mode is True


def test_load_ignores_corrupt_file(app_dir):
    s = Settings()
    s.file.write_text("not valid json", encoding="utf-8")
    # Should not raise; values should fall back to previously-set defaults
    s.load()
    assert s.theme_mode == "system"


def test_load_ignores_missing_keys(app_dir):
    settings_path = app_dir / "settings.json"
    settings_path.write_text(json.dumps({"theme_mode": "light"}), encoding="utf-8")

    s = Settings()
    assert s.theme_mode == "light"
    assert s.enable_edit_mode is False  # default preserved


def test_reset_to_defaults_clears_changes(app_dir):
    s = Settings()
    s.theme_mode = "dark"
    s.enable_edit_mode = True
    s.font_size_multiplier = 1.25
    s.save()

    s.reset_to_defaults()

    assert s.theme_mode == "system"
    assert s.enable_edit_mode is False
    assert s.font_size_multiplier == 1.0

    # And persisted to disk
    on_disk = json.loads(s.file.read_text(encoding="utf-8"))
    assert on_disk["theme_mode"] == "system"
    assert on_disk["enable_edit_mode"] is False
