import ctypes
from ctypes import Structure, c_uint32, c_uint16, c_wchar, c_long, c_void_p, wintypes
from display_presets.display_config import DisplayConfigManager, LUID

# ---------------------------------------------------------------------------
# DisplayConfigGetDeviceInfo – get friendly monitor name
# ---------------------------------------------------------------------------

DISPLAYCONFIG_DEVICE_INFO_GET_TARGET_NAME = 2


class _DeviceInfoHeader(Structure):
    _fields_ = [
        ('type', c_uint32),
        ('size', c_uint32),
        ('adapterId', LUID),
        ('id', c_uint32),
    ]


class _TargetDeviceNameFlags(Structure):
    _fields_ = [('value', c_uint32)]


class _TargetDeviceName(Structure):
    _fields_ = [
        ('header', _DeviceInfoHeader),
        ('flags', _TargetDeviceNameFlags),
        ('outputTechnology', c_uint32),
        ('edidManufactureId', c_uint16),
        ('edidProductCodeId', c_uint16),
        ('connectorInstance', c_uint32),
        ('monitorFriendlyDeviceName', c_wchar * 64),
        ('monitorDevicePath', c_wchar * 128),
    ]


_DisplayConfigGetDeviceInfo = ctypes.windll.user32.DisplayConfigGetDeviceInfo
_DisplayConfigGetDeviceInfo.argtypes = [c_void_p]
_DisplayConfigGetDeviceInfo.restype = wintypes.LONG


def _get_monitor_device_info(adapter_id: dict, target_id: int) -> dict:
    """Return a dict with friendly name, device path, and EDID identifiers for
    the monitor at the given adapter/target. Missing fields are None / empty."""
    info = _TargetDeviceName()
    info.header.type = DISPLAYCONFIG_DEVICE_INFO_GET_TARGET_NAME
    info.header.size = ctypes.sizeof(_TargetDeviceName)
    info.header.adapterId.LowPart = adapter_id['LowPart']
    info.header.adapterId.HighPart = adapter_id['HighPart']
    info.header.id = target_id
    result = _DisplayConfigGetDeviceInfo(ctypes.addressof(info))
    if result != 0:
        return {'name': None, 'devicePath': None, 'edidManufactureId': 0, 'edidProductCodeId': 0}
    name = info.monitorFriendlyDeviceName
    device_path = info.monitorDevicePath
    return {
        'name': name.strip() if name else None,
        'devicePath': device_path.strip() if device_path else None,
        'edidManufactureId': int(info.edidManufactureId),
        'edidProductCodeId': int(info.edidProductCodeId),
    }


def _get_monitor_name(adapter_id: dict, target_id: int) -> str | None:
    return _get_monitor_device_info(adapter_id, target_id).get('name')


# ---------------------------------------------------------------------------
# GetDpiForMonitor – scale factor
# ---------------------------------------------------------------------------

class _RECT(Structure):
    _fields_ = [('left', c_long), ('top', c_long), ('right', c_long), ('bottom', c_long)]


def _get_scale_factor(x: int, y: int) -> float:
    try:
        rect = _RECT(x, y, x + 2, y + 2)
        hmon = ctypes.windll.user32.MonitorFromRect(ctypes.byref(rect), 2)
        if not hmon:
            return 1.0
        dpi_x = c_uint32(96)
        dpi_y = c_uint32(96)
        hr = ctypes.windll.shcore.GetDpiForMonitor(
            hmon, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y)
        )
        if hr == 0:
            raw = dpi_x.value / 96.0
            for common in (1.0, 1.25, 1.5, 1.75, 2.0, 2.5, 3.0):
                if abs(raw - common) < 0.13:
                    return common
            return round(raw, 2)
    except Exception:
        pass
    return 1.0


# ---------------------------------------------------------------------------
# Path status flags
# ---------------------------------------------------------------------------

_PATH_SOURCE_IN_USE = 0x00000001
_MODE_IDX_INVALID = 0xFFFFFFFF
_ROTATION_MAP = {1: 0, 2: 90, 3: 180, 4: 270}
_OUTPUT_TECH = {
    0: 'Other', 1: 'VGA', 2: 'S-Video', 3: 'Composite',
    4: 'Component', 5: 'DVI', 6: 'HDMI', 7: 'LVDS',
    10: 'DisplayPort', 11: 'eDP', 14: 'SDTVDongle',
    15: 'Miracast',
}
_PIXEL_FORMAT = {1: '8bpp', 2: '16bpp', 3: '24bpp', 4: '32bpp'}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_current_displays() -> list[dict]:
    """Return normalized monitor list from the current Windows display config."""
    manager = DisplayConfigManager()
    raw = manager.get_current()

    # modeInfoIdx in path source/target info is the ARRAY INDEX into the modes
    # list, not the mode's own 'id' field (which is the adapter port ID).
    source_modes: dict = {}  # array_index -> sourceMode dict
    target_modes: dict = {}  # array_index -> targetMode dict

    for idx, mode in enumerate(raw['modes']):
        if mode['infoType'] == 1:
            source_modes[idx] = mode['sourceMode']
        elif mode['infoType'] == 2:
            target_modes[idx] = mode['targetMode']

    monitors = []

    for i, path in enumerate(raw['paths']):
        src = path['sourceInfo']
        tgt = path['targetInfo']

        if not (src['statusFlags'] & _PATH_SOURCE_IN_USE):
            continue

        src_idx = src['modeInfoIdx']
        tgt_idx = tgt['modeInfoIdx']

        src_mode = source_modes.get(src_idx) if src_idx != _MODE_IDX_INVALID else None
        tgt_mode = target_modes.get(tgt_idx) if tgt_idx != _MODE_IDX_INVALID else None

        if src_mode is None:
            continue

        x = src_mode['position']['x']
        y = src_mode['position']['y']
        width = src_mode['width']
        height = src_mode['height']

        refresh_rate = 60
        signal = tgt_mode.get('targetVideoSignalInfo', {}) if tgt_mode else {}
        if signal:
            vsync = signal.get('vSyncFreq', {})
            if vsync.get('Denominator', 0) > 0:
                refresh_rate = round(vsync['Numerator'] / vsync['Denominator'])

        rotation = _ROTATION_MAP.get(tgt.get('rotation', 1), 0)
        is_primary = (x == 0 and y == 0)

        device_info = _get_monitor_device_info(tgt['adapterId'], tgt['id'])
        name = device_info.get('name')
        if not name:
            name = f'Display {len(monitors) + 1}'

        scale_factor = _get_scale_factor(x if is_primary else x + 1, y if is_primary else y + 1)

        out_tech = tgt.get('outputTechnology', 0)
        connector = _OUTPUT_TECH.get(out_tech, f'Unknown ({out_tech})')
        if out_tech == 0x80000000:
            connector = 'Internal'

        active = signal.get('activeSize', {})
        native_w = active.get('cx', width)
        native_h = active.get('cy', height)

        color_depth = _PIXEL_FORMAT.get(src_mode.get('pixelFormat', 0), 'Unknown')

        monitors.append({
            'id': f'monitor_{i}',
            'name': name,
            'x': x,
            'y': y,
            'width': width,
            'height': height,
            'refreshRate': refresh_rate,
            'rotation': rotation,
            'isPrimary': is_primary,
            'scaleFactor': scale_factor,
            'connector': connector,
            'nativeWidth': native_w,
            'nativeHeight': native_h,
            'colorDepth': color_depth,
            'devicePath': device_info.get('devicePath'),
            'edidManufactureId': device_info.get('edidManufactureId', 0),
            'edidProductCodeId': device_info.get('edidProductCodeId', 0),
        })

    return monitors
