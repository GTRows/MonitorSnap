import pytest

from display_presets import displays as displays_mod
from display_presets.display_config import DisplayConfigManager


_INVALID = 0xFFFFFFFF


def _make_path(src_id, tgt_id, mode_idx, adapter_low=1, adapter_high=0):
    return {
        'sourceInfo': {
            'adapterId': {'LowPart': adapter_low, 'HighPart': adapter_high},
            'id': src_id,
            'modeInfoIdx': mode_idx,
            'statusFlags': 0,
        },
        'targetInfo': {
            'adapterId': {'LowPart': adapter_low, 'HighPart': adapter_high},
            'id': tgt_id,
            'modeInfoIdx': _INVALID,
            'outputTechnology': 0,
            'rotation': 1,
            'scaling': 128,
            'refreshRate': {'Numerator': 60, 'Denominator': 1},
            'scanLineOrdering': 0,
            'targetAvailable': True,
            'statusFlags': 0,
        },
        'flags': 1,
    }


def _make_source_mode(idx_id, x, y, w, h, adapter_low=1, adapter_high=0):
    return {
        'infoType': 1,
        'id': idx_id,
        'adapterId': {'LowPart': adapter_low, 'HighPart': adapter_high},
        'sourceMode': {
            'width': w,
            'height': h,
            'pixelFormat': 1,
            'position': {'x': x, 'y': y},
        },
    }


def _two_path_config():
    """Two active paths: path[0] at (0,0) 1920x1080, path[1] at (1920,0) 1920x1080."""
    return {
        'paths': [
            _make_path(src_id=0, tgt_id=100, mode_idx=0),
            _make_path(src_id=1, tgt_id=200, mode_idx=1),
        ],
        'modes': [
            _make_source_mode(0, 0, 0, 1920, 1080),
            _make_source_mode(1, 1920, 0, 1920, 1080),
        ],
    }


@pytest.fixture
def device_info_map(monkeypatch):
    """Let tests declare which devicePath/edid each (adapter, target_id) returns."""
    registry = {}

    def fake(adapter_id, target_id):
        key = (adapter_id.get('LowPart'), adapter_id.get('HighPart'), target_id)
        return registry.get(key, {
            'name': 'Unknown',
            'devicePath': None,
            'edidManufactureId': 0,
            'edidProductCodeId': 0,
        })

    monkeypatch.setattr(displays_mod, '_get_monitor_device_info', fake)
    return registry


def test_rebuild_matches_by_device_path_even_when_ids_shift(device_info_map):
    """When path ordering differs from the saved monitor's id, devicePath
    matching must still route each monitor to the right path."""
    device_info_map[(1, 0, 100)] = {'devicePath': r'\\?\DISPLAY#LEFT', 'name': '',
                                     'edidManufactureId': 0, 'edidProductCodeId': 0}
    device_info_map[(1, 0, 200)] = {'devicePath': r'\\?\DISPLAY#RIGHT', 'name': '',
                                     'edidManufactureId': 0, 'edidProductCodeId': 0}

    cfg = _two_path_config()
    mgr = DisplayConfigManager()

    # Incoming monitor list uses ids that intentionally mismatch path ordering,
    # so monitor_N fallback would be wrong. devicePath must win.
    monitors = [
        {'id': 'monitor_1', 'devicePath': r'\\?\DISPLAY#LEFT',
         'x': 500, 'y': 10, 'width': 1920, 'height': 1080},
        {'id': 'monitor_0', 'devicePath': r'\\?\DISPLAY#RIGHT',
         'x': 2420, 'y': 10, 'width': 1920, 'height': 1080},
    ]

    out = mgr.rebuild_config_for_monitors(cfg, monitors)

    # path[0] (target 100, LEFT) should move to (500, 10).
    left_mode_idx = out['paths'][0]['sourceInfo']['modeInfoIdx']
    left_pos = out['modes'][left_mode_idx]['sourceMode']['position']
    assert (left_pos['x'], left_pos['y']) == (500, 10)

    # path[1] (target 200, RIGHT) should move to (2420, 10).
    right_mode_idx = out['paths'][1]['sourceInfo']['modeInfoIdx']
    right_pos = out['modes'][right_mode_idx]['sourceMode']['position']
    assert (right_pos['x'], right_pos['y']) == (2420, 10)


def test_rebuild_falls_back_to_monitor_n_when_no_device_path(device_info_map):
    cfg = _two_path_config()
    mgr = DisplayConfigManager()

    # No devicePath on monitors and no entries in registry -> monitor_N fallback.
    monitors = [
        {'id': 'monitor_0', 'x': 100, 'y': 0, 'width': 1920, 'height': 1080},
        {'id': 'monitor_1', 'x': 2020, 'y': 0, 'width': 1920, 'height': 1080},
    ]

    out = mgr.rebuild_config_for_monitors(cfg, monitors)

    pos0 = out['modes'][out['paths'][0]['sourceInfo']['modeInfoIdx']]['sourceMode']['position']
    pos1 = out['modes'][out['paths'][1]['sourceInfo']['modeInfoIdx']]['sourceMode']['position']
    assert (pos0['x'], pos0['y']) == (100, 0)
    assert (pos1['x'], pos1['y']) == (2020, 0)


def test_rebuild_device_path_takes_precedence_over_monitor_n(device_info_map):
    """If a monitor carries a devicePath, it must NOT be routed by its id."""
    device_info_map[(1, 0, 100)] = {'devicePath': r'\\?\DISPLAY#A', 'name': '',
                                     'edidManufactureId': 0, 'edidProductCodeId': 0}
    device_info_map[(1, 0, 200)] = {'devicePath': r'\\?\DISPLAY#B', 'name': '',
                                     'edidManufactureId': 0, 'edidProductCodeId': 0}

    cfg = _two_path_config()
    mgr = DisplayConfigManager()

    # monitor 0 says devicePath=B -> path index 1. id 'monitor_0' would
    # otherwise send it to path index 0. Result: path[1] position wins.
    monitors = [
        {'id': 'monitor_0', 'devicePath': r'\\?\DISPLAY#B',
         'x': 777, 'y': 0, 'width': 1920, 'height': 1080},
    ]

    out = mgr.rebuild_config_for_monitors(cfg, monitors)

    pos1 = out['modes'][out['paths'][1]['sourceInfo']['modeInfoIdx']]['sourceMode']['position']
    assert (pos1['x'], pos1['y']) == (777, 0)

    # path[0] should be untouched.
    pos0 = out['modes'][out['paths'][0]['sourceInfo']['modeInfoIdx']]['sourceMode']['position']
    assert (pos0['x'], pos0['y']) == (0, 0)


def test_rebuild_unknown_device_path_falls_back_to_monitor_n(device_info_map):
    device_info_map[(1, 0, 100)] = {'devicePath': r'\\?\DISPLAY#A', 'name': '',
                                     'edidManufactureId': 0, 'edidProductCodeId': 0}
    device_info_map[(1, 0, 200)] = {'devicePath': r'\\?\DISPLAY#B', 'name': '',
                                     'edidManufactureId': 0, 'edidProductCodeId': 0}

    cfg = _two_path_config()
    mgr = DisplayConfigManager()

    # devicePath doesn't match anything current -> should still find path via id.
    monitors = [
        {'id': 'monitor_1', 'devicePath': r'\\?\DISPLAY#GONE',
         'x': 999, 'y': 0, 'width': 1920, 'height': 1080},
    ]

    out = mgr.rebuild_config_for_monitors(cfg, monitors)

    pos1 = out['modes'][out['paths'][1]['sourceInfo']['modeInfoIdx']]['sourceMode']['position']
    assert (pos1['x'], pos1['y']) == (999, 0)
