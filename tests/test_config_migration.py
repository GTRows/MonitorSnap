import os
import sys
import pytest

from display_presets import config


@pytest.fixture
def appdata_root(tmp_path, monkeypatch):
    monkeypatch.setenv('APPDATA', str(tmp_path))
    monkeypatch.delenv('MONITORSNAP_DATA_DIR', raising=False)
    monkeypatch.setattr(sys, 'platform', 'win32')
    return tmp_path


def test_creates_new_dir_when_no_legacy(appdata_root):
    target = appdata_root / 'MonitorSnap'
    assert not target.exists()

    got = config.get_app_dir()

    assert got == target
    assert target.is_dir()


def test_migrates_legacy_dir_when_new_missing(appdata_root):
    legacy = appdata_root / 'DisplayPresets'
    legacy.mkdir()
    (legacy / 'settings.json').write_text('{"theme": "dark"}', encoding='utf-8')
    presets = legacy / 'presets'
    presets.mkdir()
    (presets / 'a.json').write_text('{}', encoding='utf-8')

    got = config.get_app_dir()

    target = appdata_root / 'MonitorSnap'
    assert got == target
    assert target.is_dir()
    assert not legacy.exists()
    assert (target / 'settings.json').read_text(encoding='utf-8') == '{"theme": "dark"}'
    assert (target / 'presets' / 'a.json').exists()


def test_does_not_overwrite_existing_new_dir(appdata_root):
    legacy = appdata_root / 'DisplayPresets'
    legacy.mkdir()
    (legacy / 'settings.json').write_text('legacy', encoding='utf-8')
    new = appdata_root / 'MonitorSnap'
    new.mkdir()
    (new / 'settings.json').write_text('new', encoding='utf-8')

    got = config.get_app_dir()

    assert got == new
    # Legacy dir is preserved untouched so the user can recover it.
    assert legacy.exists()
    assert (legacy / 'settings.json').read_text(encoding='utf-8') == 'legacy'
    assert (new / 'settings.json').read_text(encoding='utf-8') == 'new'


def test_data_dir_override_takes_precedence(tmp_path, monkeypatch):
    monkeypatch.setenv('APPDATA', str(tmp_path / 'roaming'))
    override = tmp_path / 'portable' / 'data'
    monkeypatch.setenv('MONITORSNAP_DATA_DIR', str(override))

    got = config.get_app_dir()

    assert got == override
    assert override.is_dir()


def test_exe_path_prefers_monitorsnap_env(monkeypatch):
    monkeypatch.setenv('MONITORSNAP_APP_EXE', r'C:\Apps\MonitorSnap.exe')
    monkeypatch.setenv('DISPLAYPRESETS_APP_EXE', r'C:\Old\DisplayPresets.exe')

    assert config.get_exe_path() == '"C:\\Apps\\MonitorSnap.exe"'


def test_exe_path_falls_back_to_legacy_env(monkeypatch):
    monkeypatch.delenv('MONITORSNAP_APP_EXE', raising=False)
    monkeypatch.setenv('DISPLAYPRESETS_APP_EXE', r'C:\Old\DisplayPresets.exe')

    assert config.get_exe_path() == '"C:\\Old\\DisplayPresets.exe"'
