import copy
import ctypes
from types import SimpleNamespace
from typing import Any

import pytest

from display_presets import displays as displays_mod
from display_presets import display_config as display_config_mod
from display_presets import server
from display_presets.display_config import DisplayConfigManager
from display_presets.store import PresetStore


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


def test_apply_remaps_saved_target_id_by_monitor_identity(device_info_map, display_api) -> None:
    cfg = {
        'paths': [
            {
                **_make_path(src_id=0, tgt_id=111, mode_idx=0),
                'monitorIdentity': {
                    'name': 'Stable Display',
                    'devicePath': r'\\?\DISPLAY#STABLE',
                    'edidManufactureId': 123,
                    'edidProductCodeId': 456,
                },
            },
        ],
        'modes': [
            _make_source_mode(0, 100, 0, 1920, 1080),
        ],
    }

    current_target_id = 333
    device_info_map[(1, 0, current_target_id)] = {
        'name': 'Stable Display',
        'devicePath': r'\\?\DISPLAY#STABLE',
        'edidManufactureId': 123,
        'edidProductCodeId': 456,
    }
    current = _mode_config(1920, 1080)
    current['paths'][0]['targetInfo']['id'] = current_target_id
    display_api.configure(current)

    result = DisplayConfigManager().apply(cfg)

    assert result == 0
    assert display_api.calls
    assert all([p.targetInfo.id for p in paths] == [current_target_id]
               for paths, modes, flags in display_api.calls)
    assert display_api.modes[0].modeInfo.sourceMode.position.x == 100


def _mode_config(
    width: int = 2560,
    height: int = 1440,
    refresh: tuple[int, int] = (60, 1),
    clone: bool = False,
) -> dict[str, Any]:
    paths = [_make_path(0, 100, 0)]
    if clone:
        paths.append(_make_path(0, 200, 0))
    modes = [_make_source_mode(0, 0, 0, width, height)]
    for path in paths:
        path['targetInfo']['modeInfoIdx'] = len(modes)
        path['targetInfo']['scaling'] = 1
        path['targetInfo']['refreshRate'] = {
            'Numerator': refresh[0], 'Denominator': refresh[1],
        }
        path['targetInfo']['scanLineOrdering'] = 1
        modes.append({
            'infoType': 2,
            'id': path['targetInfo']['id'],
            'adapterId': {'LowPart': 1, 'HighPart': 0},
            'targetMode': {'targetVideoSignalInfo': {
                'pixelRate': width * height * refresh[0] // refresh[1],
                'hSyncFreq': {'Numerator': height * refresh[0], 'Denominator': refresh[1]},
                'vSyncFreq': {'Numerator': refresh[0], 'Denominator': refresh[1]},
                'activeSize': {'cx': width, 'cy': height},
                'totalSize': {'cx': width, 'cy': height},
                'videoStandard': 0,
                'scanLineOrdering': 1,
            }},
        })
    return {'paths': paths, 'modes': modes}


@pytest.fixture
def display_api(monkeypatch, device_info_map) -> SimpleNamespace:
    api = SimpleNamespace(
        paths=[], modes=[], calls=[], topology_result=0, mode_result=0,
        size_error=0, query_error=0, ignore_changes=False, selected_refresh=None,
        extra_mode_capacity=0,
    )

    def configure(cfg: dict[str, Any]) -> None:
        api.paths = []
        api.modes = []
        for saved in cfg['paths']:
            path = display_config_mod.DISPLAYCONFIG_PATH_INFO()
            for name in ('sourceInfo', 'targetInfo'):
                info = getattr(path, name)
                for field, value in saved[name].items():
                    if isinstance(value, dict):
                        for member, number in value.items():
                            setattr(getattr(info, field), member, number)
                    else:
                        setattr(info, field, value)
            path.sourceInfo.statusFlags = 1
            path.flags = 1
            api.paths.append(path)
        for saved in cfg['modes']:
            mode = display_config_mod.DISPLAYCONFIG_MODE_INFO()
            mode.infoType = saved['infoType']
            mode.id = saved['id']
            mode.adapterId.LowPart = 1
            if mode.infoType == 1:
                source = mode.modeInfo.sourceMode
                for field in ('width', 'height', 'pixelFormat'):
                    setattr(source, field, saved['sourceMode'][field])
                source.position.x = saved['sourceMode']['position']['x']
                source.position.y = saved['sourceMode']['position']['y']
            else:
                signal = mode.modeInfo.targetMode.targetVideoSignalInfo
                saved_signal = saved['targetMode']['targetVideoSignalInfo']
                for field, value in saved_signal.items():
                    if isinstance(value, dict):
                        for member, number in value.items():
                            setattr(getattr(signal, field), member, number)
                    else:
                        setattr(signal, field, value)
            api.modes.append(mode)

    def sizes(flags: int, path_count: Any, mode_count: Any) -> int:
        if flags == 2 and api.size_error:
            return api.size_error
        path_count._obj.value = len(api.paths)
        mode_count._obj.value = len(api.modes) + api.extra_mode_capacity
        return 0

    def query(
        flags: int, path_count: Any, paths: Any, mode_count: Any,
        modes: Any, topology: Any,
    ) -> int:
        if flags == 2 and api.query_error:
            return api.query_error
        if len(paths) < len(api.paths) or len(modes) < len(api.modes):
            return 122
        path_count._obj.value = len(api.paths)
        mode_count._obj.value = len(api.modes)
        for index, path in enumerate(api.paths):
            ctypes.memmove(ctypes.byref(paths[index]), ctypes.byref(path), ctypes.sizeof(path))
        for index, mode in enumerate(api.modes):
            ctypes.memmove(ctypes.byref(modes[index]), ctypes.byref(mode), ctypes.sizeof(mode))
        return 0

    def set_config(
        path_count: int, paths: Any, mode_count: int, modes: Any, flags: int,
    ) -> int:
        requested_paths = [copy.deepcopy(paths[i]) for i in range(path_count)]
        requested_modes = [copy.deepcopy(modes[i]) for i in range(mode_count)]
        api.calls.append((requested_paths, requested_modes, flags))
        if flags & 0x10:
            return api.topology_result
        if api.mode_result or api.ignore_changes:
            return api.mode_result
        api.paths = copy.deepcopy(requested_paths)
        api.modes = copy.deepcopy(requested_modes)
        for path in api.paths:
            if path.targetInfo.modeInfoIdx != _INVALID:
                continue
            mode = display_config_mod.DISPLAYCONFIG_MODE_INFO()
            mode.infoType = 2
            mode.id = path.targetInfo.id
            mode.adapterId = path.targetInfo.adapterId
            signal = mode.modeInfo.targetMode.targetVideoSignalInfo
            signal.vSyncFreq = path.targetInfo.refreshRate
            if api.selected_refresh is not None:
                signal.vSyncFreq.Numerator, signal.vSyncFreq.Denominator = api.selected_refresh
            signal.scanLineOrdering = path.targetInfo.scanLineOrdering
            source = api.modes[path.sourceInfo.modeInfoIdx].modeInfo.sourceMode
            signal.activeSize.cx = source.width
            signal.activeSize.cy = source.height
            path.targetInfo.modeInfoIdx = len(api.modes)
            api.modes.append(mode)
        return 0

    api.configure = configure
    monkeypatch.setattr(display_config_mod, 'GetDisplayConfigBufferSizes', sizes)
    monkeypatch.setattr(display_config_mod, 'QueryDisplayConfig', query)
    monkeypatch.setattr(display_config_mod, 'SetDisplayConfig', set_config)
    return api


@pytest.mark.parametrize('current,saved', [
    ((2560, 1440), (5120, 1440)),
    ((5120, 1440), (2560, 1440)),
    ((1920, 1080), (1920, 1200)),
])
def test_apply_restores_resolution_without_position_changes(display_api, current, saved) -> None:
    display_api.configure(_mode_config(*current))

    assert DisplayConfigManager().apply(_mode_config(*saved)) == 0

    source = display_api.modes[0].modeInfo.sourceMode
    assert (source.width, source.height) == saved


@pytest.mark.parametrize('current,saved', [
    ((60, 1), (144, 1)), ((144, 1), (60, 1)), ((60, 1), (60000, 1001)),
])
def test_apply_restores_refresh_without_layout_changes(display_api, current, saved) -> None:
    display_api.configure(_mode_config(refresh=current))

    assert DisplayConfigManager().apply(_mode_config(refresh=saved)) == 0

    path = display_api.paths[0]
    mode = display_api.modes[path.targetInfo.modeInfoIdx].modeInfo.targetMode
    signal = mode.targetVideoSignalInfo
    assert (signal.vSyncFreq.Numerator, signal.vSyncFreq.Denominator) == saved


def test_apply_uses_saved_signal_refresh_instead_of_path_refresh(display_api) -> None:
    display_api.configure(_mode_config(refresh=(60, 1)))
    saved = _mode_config(refresh=(144, 1))
    saved['paths'][0]['targetInfo']['refreshRate'] = {'Numerator': 60, 'Denominator': 1}

    assert DisplayConfigManager().apply(saved) == 0

    path = display_api.paths[0]
    mode = display_api.modes[path.targetInfo.modeInfoIdx].modeInfo.targetMode
    rate = mode.targetVideoSignalInfo.vSyncFreq
    assert (rate.Numerator, rate.Denominator) == (144, 1)


def test_apply_updates_every_target_in_shared_source_clone_group(display_api) -> None:
    display_api.configure(_mode_config(clone=True))
    saved = _mode_config(5120, 1440, (144, 1), clone=True)
    saved['modes'][2]['targetMode']['targetVideoSignalInfo']['vSyncFreq'] = {
        'Numerator': 60, 'Denominator': 1,
    }
    saved['modes'][2]['targetMode']['targetVideoSignalInfo']['pixelRate'] = 442368000
    saved['modes'][2]['targetMode']['targetVideoSignalInfo']['hSyncFreq'] = {
        'Numerator': 86400, 'Denominator': 1,
    }

    assert DisplayConfigManager().apply(saved) == 0

    paths, modes, flags = display_api.calls[-1]
    assert [p.sourceInfo.modeInfoIdx for p in paths] == [0, 0]
    assert modes[0].modeInfo.sourceMode.width == 5120
    signals = [modes[p.targetInfo.modeInfoIdx].modeInfo.targetMode for p in paths]
    assert [m.targetVideoSignalInfo.vSyncFreq.Numerator for m in signals] == [144, 60]
    assert not flags & 0x400


@pytest.mark.parametrize('rotation', [2, 3, 4])
def test_apply_restores_rotation(display_api, rotation) -> None:
    display_api.configure(_mode_config())
    saved = _mode_config()
    saved['paths'][0]['targetInfo']['rotation'] = rotation

    assert DisplayConfigManager().apply(saved) == 0

    assert display_api.paths[0].targetInfo.rotation == rotation


def test_apply_restores_source_pixel_format(display_api) -> None:
    display_api.configure(_mode_config())
    saved = _mode_config()
    saved['modes'][0]['sourceMode']['pixelFormat'] = 4

    assert DisplayConfigManager().apply(saved) == 0

    assert display_api.modes[0].modeInfo.sourceMode.pixelFormat == 4


@pytest.mark.parametrize('error', [31, 87])
def test_apply_returns_phase_two_error(display_api, error) -> None:
    display_api.configure(_mode_config())
    display_api.mode_result = error
    saved = _mode_config()
    saved['modes'][0]['sourceMode']['position']['x'] = 100

    assert DisplayConfigManager().apply(saved) == error


@pytest.mark.parametrize('error_field', ['size_error', 'query_error'])
def test_apply_returns_phase_two_query_errors(display_api, error_field) -> None:
    display_api.configure(_mode_config())
    setattr(display_api, error_field, 31)

    assert DisplayConfigManager().apply(_mode_config()) == 31
    assert len(display_api.calls) == 1


def test_apply_returns_topology_error_without_applying_modes(display_api) -> None:
    display_api.configure(_mode_config())
    display_api.topology_result = 87

    assert DisplayConfigManager().apply(_mode_config(5120, 1440)) == 87
    assert len(display_api.calls) == 1


def test_apply_skips_mode_update_when_saved_settings_match(display_api) -> None:
    display_api.configure(_mode_config(refresh=(60000, 1000)))

    assert DisplayConfigManager().apply(_mode_config(refresh=(60, 1))) == 0
    assert len(display_api.calls) == 1


@pytest.mark.parametrize('saved', [
    _mode_config(5120, 1440), _mode_config(refresh=(144, 1)),
])
def test_apply_rejects_success_when_driver_did_not_restore_settings(display_api, saved) -> None:
    display_api.configure(_mode_config())
    display_api.ignore_changes = True

    with pytest.raises(RuntimeError, match='did not restore'):
        DisplayConfigManager().apply(saved)


def test_rebuild_applies_edited_refresh_rate(device_info_map) -> None:
    cfg = _mode_config()
    monitor = {
        'id': 'monitor_0', 'x': 0, 'y': 0, 'width': 2560, 'height': 1440,
        'refreshRate': 144, 'rotation': 0,
    }

    rebuilt = DisplayConfigManager().rebuild_config_for_monitors(cfg, [monitor])

    target = rebuilt['paths'][0]['targetInfo']
    assert target['refreshRate'] == {'Numerator': 144, 'Denominator': 1}
    assert target['modeInfoIdx'] == _INVALID
    assert cfg['paths'][0]['targetInfo']['refreshRate']['Numerator'] == 60


@pytest.mark.parametrize('rotation,expected', [(0, 1), (90, 2), (180, 3), (270, 4)])
def test_rebuild_applies_edited_rotation(device_info_map, rotation, expected) -> None:
    monitor = {
        'id': 'monitor_0', 'x': 0, 'y': 0, 'width': 2560, 'height': 1440,
        'refreshRate': 60, 'rotation': rotation,
    }

    rebuilt = DisplayConfigManager().rebuild_config_for_monitors(_mode_config(), [monitor])

    assert rebuilt['paths'][0]['targetInfo']['rotation'] == expected


def test_rebuild_preserves_fractional_refresh_during_layout_edit(device_info_map) -> None:
    cfg = _mode_config(refresh=(60000, 1001))
    monitor = {
        'id': 'monitor_0', 'x': 100, 'y': 0, 'width': 2560, 'height': 1440,
        'refreshRate': 60, 'rotation': 0,
    }

    rebuilt = DisplayConfigManager().rebuild_config_for_monitors(cfg, [monitor])

    target = rebuilt['paths'][0]['targetInfo']
    assert target['refreshRate'] == {'Numerator': 60000, 'Denominator': 1001}
    assert target['modeInfoIdx'] == 1


def test_rebuild_discards_old_target_timing_after_resolution_edit(device_info_map) -> None:
    monitor = {'id': 'monitor_0', 'x': 0, 'y': 0, 'width': 5120, 'height': 1440}

    rebuilt = DisplayConfigManager().rebuild_config_for_monitors(_mode_config(), [monitor])

    assert rebuilt['paths'][0]['targetInfo']['modeInfoIdx'] == _INVALID


def test_apply_restores_saved_output_signal_with_same_source_resolution(display_api) -> None:
    current = _mode_config(1920, 1080)
    current['paths'][0]['targetInfo']['scaling'] = 3
    current['modes'][1]['targetMode']['targetVideoSignalInfo']['activeSize'] = {
        'cx': 3840, 'cy': 2160,
    }
    display_api.configure(current)
    saved = copy.deepcopy(current)
    saved['modes'][1]['targetMode']['targetVideoSignalInfo']['activeSize'] = {
        'cx': 2560, 'cy': 1440,
    }

    assert DisplayConfigManager().apply(saved) == 0

    path = display_api.paths[0]
    mode = display_api.modes[path.targetInfo.modeInfoIdx].modeInfo.targetMode
    signal = mode.targetVideoSignalInfo
    assert (signal.activeSize.cx, signal.activeSize.cy) == (2560, 1440)


def test_apply_accepts_driver_timing_for_edited_nominal_refresh(display_api) -> None:
    display_api.configure(_mode_config())
    display_api.selected_refresh = (143972, 1000)
    monitor = {
        'id': 'monitor_0', 'x': 0, 'y': 0, 'width': 2560, 'height': 1440,
        'refreshRate': 144,
    }
    manager = DisplayConfigManager()
    rebuilt = manager.rebuild_config_for_monitors(_mode_config(), [monitor])

    assert manager.apply(rebuilt) == 0
    assert rebuilt['paths'][0]['targetInfo']['modeInfoIdx'] == _INVALID


def test_apply_does_not_round_captured_refresh_rates(display_api) -> None:
    display_api.configure(_mode_config())
    display_api.ignore_changes = True

    with pytest.raises(RuntimeError, match='did not restore'):
        DisplayConfigManager().apply(_mode_config(refresh=(60000, 1001)))


def test_apply_adds_missing_target_mode_when_query_returns_fewer_modes(display_api) -> None:
    current = _mode_config()
    current['paths'][0]['targetInfo']['modeInfoIdx'] = _INVALID
    current['modes'] = current['modes'][:1]
    display_api.configure(current)
    display_api.extra_mode_capacity = 2

    assert DisplayConfigManager().apply(_mode_config(5120, 1440)) == 0

    paths, modes, flags = display_api.calls[-1]
    assert len(modes) == 2
    assert paths[0].targetInfo.modeInfoIdx == 1
    assert modes[1].id == 100
    assert modes[1].adapterId.LowPart == 1


@pytest.mark.parametrize('route', ['apply', 'test', 'test-layout'])
@pytest.mark.parametrize('failure', ['api_error', 'settings_not_restored'])
def test_display_routes_report_apply_failures(
    app_dir, monkeypatch, display_api, route, failure,
) -> None:
    display_api.configure(_mode_config())
    if failure == 'api_error':
        display_api.mode_result = 87
    else:
        display_api.ignore_changes = True
    store = PresetStore()
    preset = store.create('Resolution test', [], config=_mode_config(5120, 1440))
    monkeypatch.setattr(server, '_store', store)
    handler = server._Handler.__new__(server._Handler)
    responses = []
    handler._json = lambda data, status=200: responses.append((status, data))
    handler._read_body = lambda: {'monitors': [{
        'id': 'monitor_0', 'x': 0, 'y': 0, 'width': 5120, 'height': 1440,
        'refreshRate': 60, 'rotation': 0,
    }]}
    path = '/displays/test-layout' if route == 'test-layout' else f"/presets/{preset['id']}/{route}"

    handler._route('POST', path)

    assert len(responses) == 1
    status, body = responses[0]
    assert status == 500
    assert ('code 87' if failure == 'api_error' else 'did not restore') in body['error']


def test_edited_refresh_survives_save_and_apply_route(app_dir, monkeypatch, display_api) -> None:
    display_api.configure(_mode_config())
    display_api.selected_refresh = (143972, 1000)
    store = PresetStore()
    preset = store.create('Refresh test', [], config=_mode_config())
    monkeypatch.setattr(server, '_store', store)
    handler = server._Handler.__new__(server._Handler)
    responses = []
    handler._json = lambda data, status=200: responses.append((status, data))
    handler._read_body = lambda: {'monitors': [{
        'id': 'monitor_0', 'x': 0, 'y': 0, 'width': 2560, 'height': 1440,
        'refreshRate': 144, 'rotation': 0,
    }]}

    handler._route('PUT', f"/presets/{preset['id']}")
    handler._route('POST', f"/presets/{preset['id']}/apply")

    assert responses[-1] == (200, {'success': True})
    target = display_api.paths[0].targetInfo
    signal = display_api.modes[target.modeInfoIdx].modeInfo.targetMode.targetVideoSignalInfo
    assert (signal.vSyncFreq.Numerator, signal.vSyncFreq.Denominator) == (143972, 1000)
