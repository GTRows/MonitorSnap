import json

import pytest

from display_presets.preset_service import PresetService


def test_save_writes_json_file(app_dir):
    svc = PresetService()
    svc.save("Work", config={"monitors": []}, hotkey="Ctrl+1")

    path = svc.dir / "Work.json"
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["config"] == {"monitors": []}
    assert data["hotkey"] == "Ctrl+1"
    assert data["created_at"] is not None


def test_save_rejects_empty_name(app_dir):
    svc = PresetService()
    with pytest.raises(ValueError):
        svc.save("   ", config={}, hotkey=None)


def test_save_sanitizes_illegal_filename_characters(app_dir):
    svc = PresetService()
    svc.save("bad/name:here?", config={}, hotkey=None)
    assert (svc.dir / "bad_name_here_.json").exists()


def test_load_returns_new_format(app_dir):
    svc = PresetService()
    svc.save("Work", config={"k": "v"}, hotkey=None)
    loaded = svc.load("Work")
    assert loaded["config"] == {"k": "v"}
    assert loaded["hotkey"] is None


def test_load_wraps_legacy_format(app_dir):
    svc = PresetService()
    legacy = {"monitors": ["m1"]}
    (svc.dir / "Old.json").write_text(json.dumps(legacy), encoding="utf-8")

    loaded = svc.load("Old")
    assert loaded["config"] == legacy
    assert loaded["hotkey"] is None
    assert loaded["created_at"] is None


def test_load_missing_raises(app_dir):
    svc = PresetService()
    with pytest.raises(FileNotFoundError):
        svc.load("Nope")


def test_list_names_returns_sorted(app_dir):
    svc = PresetService()
    svc.save("B", config={}, hotkey=None)
    svc.save("A", config={}, hotkey=None)
    assert svc.list_names() == ["A", "B"]


def test_delete_removes_file(app_dir):
    svc = PresetService()
    svc.save("Work", config={}, hotkey=None)
    svc.delete("Work")
    assert not (svc.dir / "Work.json").exists()


def test_delete_missing_raises(app_dir):
    svc = PresetService()
    with pytest.raises(FileNotFoundError):
        svc.delete("Nope")


def test_rename_moves_file(app_dir):
    svc = PresetService()
    svc.save("Old", config={}, hotkey=None)
    svc.rename("Old", "New")
    assert not (svc.dir / "Old.json").exists()
    assert (svc.dir / "New.json").exists()


def test_rename_missing_source_raises(app_dir):
    svc = PresetService()
    with pytest.raises(FileNotFoundError):
        svc.rename("Old", "New")


def test_rename_rejects_existing_target(app_dir):
    svc = PresetService()
    svc.save("A", config={}, hotkey=None)
    svc.save("B", config={}, hotkey=None)
    with pytest.raises(FileExistsError):
        svc.rename("A", "B")


def test_rename_rejects_empty_new_name(app_dir):
    svc = PresetService()
    svc.save("A", config={}, hotkey=None)
    with pytest.raises(ValueError):
        svc.rename("A", "   ")
