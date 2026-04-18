import json
import uuid

from display_presets.store import PresetStore


def test_create_returns_preset_with_uuid_and_timestamps(app_dir):
    store = PresetStore()
    preset = store.create(name="Work", monitors=[{"id": "m1"}])

    uuid.UUID(preset["id"])
    assert preset["name"] == "Work"
    assert preset["monitors"] == [{"id": "m1"}]
    assert preset["hotkey"] is None
    assert preset["config"] is None
    assert preset["createdAt"] == preset["updatedAt"]


def test_create_persists_to_disk(app_dir):
    store = PresetStore()
    preset = store.create(name="Work", monitors=[])

    path = store.dir / f"{preset['id']}.json"
    assert path.exists()
    with open(path, encoding="utf-8") as f:
        on_disk = json.load(f)
    assert on_disk == preset


def test_get_returns_none_for_missing_id(app_dir):
    store = PresetStore()
    assert store.get("missing") is None


def test_get_returns_preset_by_id(app_dir):
    store = PresetStore()
    created = store.create(name="A", monitors=[])
    assert store.get(created["id"]) == created


def test_list_all_returns_only_uuid_named_files(app_dir):
    store = PresetStore()
    store.create(name="A", monitors=[])
    store.create(name="B", monitors=[])
    # Junk file that should be ignored
    (store.dir / "not-a-uuid.json").write_text("{}", encoding="utf-8")

    names = sorted(p["name"] for p in store.list_all())
    assert names == ["A", "B"]


def test_list_all_sorts_by_created_at(app_dir):
    store = PresetStore()
    p1 = store.create(name="A", monitors=[])
    p2 = store.create(name="B", monitors=[])
    # Rewrite created_at keys so ordering is deterministic (list_all sorts by 'created_at' key)
    for p, ts in ((p1, "2024-01-01"), (p2, "2024-01-02")):
        path = store.dir / f"{p['id']}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["created_at"] = ts
        path.write_text(json.dumps(data), encoding="utf-8")

    ordered = store.list_all()
    assert [p["name"] for p in ordered] == ["A", "B"]


def test_update_modifies_allowed_fields(app_dir):
    store = PresetStore()
    preset = store.create(name="A", monitors=[])
    updated = store.update(preset["id"], {"name": "A2", "hotkey": "Ctrl+1"})
    assert updated["name"] == "A2"
    assert updated["hotkey"] == "Ctrl+1"
    assert updated["updatedAt"] >= preset["createdAt"]


def test_update_ignores_unknown_fields(app_dir):
    store = PresetStore()
    preset = store.create(name="A", monitors=[])
    updated = store.update(preset["id"], {"id": "hacked", "bogus": 1})
    assert updated["id"] == preset["id"]
    assert "bogus" not in updated


def test_update_returns_none_for_missing_id(app_dir):
    store = PresetStore()
    assert store.update("nope", {"name": "x"}) is None


def test_delete_removes_file(app_dir):
    store = PresetStore()
    preset = store.create(name="A", monitors=[])
    assert store.delete(preset["id"]) is True
    assert store.get(preset["id"]) is None


def test_delete_returns_false_for_missing(app_dir):
    store = PresetStore()
    assert store.delete("missing") is False


def test_duplicate_creates_copy_with_new_id_and_no_hotkey(app_dir):
    store = PresetStore()
    original = store.create(
        name="A", monitors=[{"id": "m1"}], hotkey="Ctrl+1"
    )
    copy = store.duplicate(original["id"])

    assert copy is not None
    assert copy["id"] != original["id"]
    assert copy["name"] == "A (Copy)"
    assert copy["hotkey"] is None
    assert copy["monitors"] == original["monitors"]


def test_duplicate_returns_none_for_missing(app_dir):
    store = PresetStore()
    assert store.duplicate("missing") is None


def test_delete_all_removes_every_uuid_file_and_reports_count(app_dir):
    store = PresetStore()
    store.create(name="A", monitors=[])
    store.create(name="B", monitors=[])
    store.create(name="C", monitors=[])
    (store.dir / "not-a-uuid.json").write_text("{}", encoding="utf-8")

    deleted = store.delete_all()

    assert deleted == 3
    assert store.list_all() == []
    # Non-UUID file is preserved.
    assert (store.dir / "not-a-uuid.json").exists()


def test_import_many_preserves_valid_uuid_ids(app_dir):
    store = PresetStore()
    known_id = str(uuid.uuid4())
    imported, skipped = store.import_many([
        {"id": known_id, "name": "Imported", "monitors": [{"id": "m1"}], "hotkey": "Ctrl+F1"}
    ])
    assert (imported, skipped) == (1, 0)
    assert store.get(known_id)["name"] == "Imported"
    assert store.get(known_id)["hotkey"] == "Ctrl+F1"
    assert store.get(known_id)["config"] is None


def test_import_many_generates_new_id_for_invalid_uuid(app_dir):
    store = PresetStore()
    imported, skipped = store.import_many([
        {"id": "not-a-uuid", "name": "X", "monitors": []}
    ])
    assert (imported, skipped) == (1, 0)
    presets = store.list_all()
    assert len(presets) == 1
    uuid.UUID(presets[0]["id"])


def test_import_many_overwrites_existing_id(app_dir):
    store = PresetStore()
    original = store.create(name="Old", monitors=[])
    imported, skipped = store.import_many([
        {"id": original["id"], "name": "New", "monitors": [{"id": "m1"}]}
    ])
    assert (imported, skipped) == (1, 0)
    assert store.get(original["id"])["name"] == "New"


def test_import_many_skips_invalid_entries(app_dir):
    store = PresetStore()
    imported, skipped = store.import_many([
        None,
        {"name": "NoMonitors"},
        {"monitors": []},
        {"name": "", "monitors": []},
        {"name": "OK", "monitors": []},
    ])
    assert (imported, skipped) == (1, 4)
