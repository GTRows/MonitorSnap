import sys
import pytest

from display_presets import autostart


def test_enable_refuses_when_not_packaged(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    monkeypatch.delenv('MONITORSNAP_APP_EXE', raising=False)
    monkeypatch.delenv('DISPLAYPRESETS_APP_EXE', raising=False)

    with pytest.raises(RuntimeError, match='packaged build'):
        autostart.enable()


def test_enable_refuses_when_exe_is_dev_electron(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    monkeypatch.setenv('MONITORSNAP_APP_EXE', r'C:\src\node_modules\electron\dist\electron.exe')

    with pytest.raises(RuntimeError, match='packaged build'):
        autostart.enable()


def test_is_packaged_true_when_frozen(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', True, raising=False)

    assert autostart._is_packaged() is True


def test_is_packaged_true_when_app_exe_is_real_product(monkeypatch):
    monkeypatch.setattr(sys, 'frozen', False, raising=False)
    monkeypatch.setenv('MONITORSNAP_APP_EXE', r'C:\Program Files\MonitorSnap\MonitorSnap.exe')

    assert autostart._is_packaged() is True
