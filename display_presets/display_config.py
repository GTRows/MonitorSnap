import ctypes
import json
from ctypes import wintypes, Structure, POINTER, c_uint32, c_int32, c_uint64, c_bool
from fractions import Fraction
from typing import Any

from display_presets.logger import get_logger

_log = get_logger('display_config')


# Win32 API structures
class LUID(Structure):
    _fields_ = [("LowPart", c_uint32), ("HighPart", c_int32)]


class DISPLAYCONFIG_RATIONAL(Structure):
    _fields_ = [("Numerator", c_uint32), ("Denominator", c_uint32)]


class DISPLAYCONFIG_PATH_SOURCE_INFO(Structure):
    _fields_ = [
        ("adapterId", LUID),
        ("id", c_uint32),
        ("modeInfoIdx", c_uint32),
        ("statusFlags", c_uint32)
    ]


class DISPLAYCONFIG_PATH_TARGET_INFO(Structure):
    _fields_ = [
        ("adapterId", LUID),
        ("id", c_uint32),
        ("modeInfoIdx", c_uint32),
        ("outputTechnology", c_uint32),
        ("rotation", c_uint32),
        ("scaling", c_uint32),
        ("refreshRate", DISPLAYCONFIG_RATIONAL),
        ("scanLineOrdering", c_uint32),
        ("targetAvailable", c_bool),
        ("statusFlags", c_uint32)
    ]


class DISPLAYCONFIG_PATH_INFO(Structure):
    _fields_ = [
        ("sourceInfo", DISPLAYCONFIG_PATH_SOURCE_INFO),
        ("targetInfo", DISPLAYCONFIG_PATH_TARGET_INFO),
        ("flags", c_uint32)
    ]


class POINTL(Structure):
    _fields_ = [("x", c_int32), ("y", c_int32)]


class RECTL(Structure):
    _fields_ = [("left", c_int32), ("top", c_int32), ("right", c_int32), ("bottom", c_int32)]


class DISPLAYCONFIG_2DREGION(Structure):
    _fields_ = [("cx", c_uint32), ("cy", c_uint32)]


class DISPLAYCONFIG_VIDEO_SIGNAL_INFO(Structure):
    _fields_ = [
        ("pixelRate", c_uint64),
        ("hSyncFreq", DISPLAYCONFIG_RATIONAL),
        ("vSyncFreq", DISPLAYCONFIG_RATIONAL),
        ("activeSize", DISPLAYCONFIG_2DREGION),
        ("totalSize", DISPLAYCONFIG_2DREGION),
        ("videoStandard", c_uint32),
        ("scanLineOrdering", c_uint32)
    ]


class DISPLAYCONFIG_TARGET_MODE(Structure):
    _fields_ = [("targetVideoSignalInfo", DISPLAYCONFIG_VIDEO_SIGNAL_INFO)]


class DISPLAYCONFIG_SOURCE_MODE(Structure):
    _fields_ = [
        ("width", c_uint32),
        ("height", c_uint32),
        ("pixelFormat", c_uint32),
        ("position", POINTL)
    ]


class DISPLAYCONFIG_DESKTOP_IMAGE_INFO(Structure):
    _fields_ = [
        ("PathSourceSize", POINTL),
        ("DesktopImageRegion", RECTL),
        ("DesktopImageClip", RECTL)
    ]


class DISPLAYCONFIG_MODE_INFO_UNION(ctypes.Union):
    _fields_ = [
        ("targetMode", DISPLAYCONFIG_TARGET_MODE),
        ("sourceMode", DISPLAYCONFIG_SOURCE_MODE),
        ("desktopImageInfo", DISPLAYCONFIG_DESKTOP_IMAGE_INFO)
    ]


class DISPLAYCONFIG_MODE_INFO(Structure):
    _fields_ = [
        ("infoType", c_uint32),
        ("id", c_uint32),
        ("adapterId", LUID),
        ("modeInfo", DISPLAYCONFIG_MODE_INFO_UNION)
    ]


# API bindings
user32 = ctypes.windll.user32

GetDisplayConfigBufferSizes = user32.GetDisplayConfigBufferSizes
GetDisplayConfigBufferSizes.argtypes = [c_uint32, POINTER(c_uint32), POINTER(c_uint32)]
GetDisplayConfigBufferSizes.restype = wintypes.LONG

QueryDisplayConfig = user32.QueryDisplayConfig
QueryDisplayConfig.argtypes = [c_uint32, POINTER(c_uint32), POINTER(DISPLAYCONFIG_PATH_INFO),
                                POINTER(c_uint32), POINTER(DISPLAYCONFIG_MODE_INFO), ctypes.c_void_p]
QueryDisplayConfig.restype = wintypes.LONG

SetDisplayConfig = user32.SetDisplayConfig
SetDisplayConfig.argtypes = [c_uint32, POINTER(DISPLAYCONFIG_PATH_INFO),
                             c_uint32, POINTER(DISPLAYCONFIG_MODE_INFO), c_uint32]
SetDisplayConfig.restype = wintypes.LONG


def _normalize_device_path(device_path: Any) -> str | None:
    if not isinstance(device_path, str) or not device_path:
        return None
    return device_path.strip().casefold()


def _edid_key(info: dict[str, Any] | None) -> tuple[int, int] | None:
    if not isinstance(info, dict):
        return None
    manufacture_id = int(info.get('edidManufactureId') or 0)
    product_code_id = int(info.get('edidProductCodeId') or 0)
    if not manufacture_id or not product_code_id:
        return None
    return manufacture_id, product_code_id


def _monitor_for_saved_path(
    monitors: list[dict[str, Any]] | None,
    path_index: int,
) -> dict[str, Any]:
    if not monitors:
        return {}
    expected_id = f'monitor_{path_index}'
    for monitor in monitors:
        if isinstance(monitor, dict) and monitor.get('id') == expected_id:
            return monitor
    if path_index < len(monitors) and isinstance(monitors[path_index], dict):
        return monitors[path_index]
    return {}


def _resolve_current_target(
    identity: dict[str, Any],
    cur_by_device_path: dict[str, dict[str, Any]],
    cur_by_edid: dict[tuple[int, int], list[dict[str, Any]]],
) -> dict[str, Any] | None:
    device_path = _normalize_device_path(identity.get('devicePath'))
    if device_path and device_path in cur_by_device_path:
        return cur_by_device_path[device_path]

    edid_key = _edid_key(identity)
    if not edid_key:
        return None

    matches = cur_by_edid.get(edid_key, [])
    if len(matches) == 1:
        return matches[0]

    monitor_name = identity.get('name')
    if isinstance(monitor_name, str) and monitor_name:
        named_matches = [m for m in matches if m.get('name') == monitor_name]
        if len(named_matches) == 1:
            return named_matches[0]

    return None


def _path_monitor_identity(path: dict[str, Any]) -> dict[str, Any]:
    identity = path.get('monitorIdentity')
    if isinstance(identity, dict):
        return identity
    return {}


def _path_target_signal(
    path: dict[str, Any], modes: list[dict[str, Any]],
) -> dict[str, Any] | None:
    index = path['targetInfo']['modeInfoIdx']
    if 0 <= index < len(modes) and modes[index].get('infoType') == 2:
        return modes[index]['targetMode']['targetVideoSignalInfo']
    return None


def _path_signal_settings(
    path: dict[str, Any], modes: list[dict[str, Any]],
) -> tuple[int, int, int]:
    target = path['targetInfo']
    rate = target['refreshRate']
    scanline = target['scanLineOrdering']
    signal = _path_target_signal(path, modes)
    if signal is not None:
        rate = signal['vSyncFreq']
        scanline = signal['scanLineOrdering']
    return rate['Numerator'], rate['Denominator'], scanline


def _same_refresh_rate(
    first: tuple[int, int], second: tuple[int, int], nominal: bool = False,
) -> bool:
    if not first[1] or not second[1]:
        return first == second
    if nominal:
        return round(first[0] / first[1]) == round(second[0] / second[1])
    return first[0] * second[1] == second[0] * first[1]


def _same_target_signal(first: dict[str, Any] | None, second: dict[str, Any]) -> bool:
    if first is None:
        return False
    for field, value in second.items():
        if field in ('hSyncFreq', 'vSyncFreq'):
            actual = first[field]
            if not _same_refresh_rate(
                (actual['Numerator'], actual['Denominator']),
                (value['Numerator'], value['Denominator']),
            ):
                return False
        elif first.get(field) != value:
            return False
    return True


class DisplayConfigManager:
    def get_current(self):
        pc, mc = c_uint32(), c_uint32()

        result = GetDisplayConfigBufferSizes(0x02, ctypes.byref(pc), ctypes.byref(mc))
        if result != 0:
            raise Exception(f"GetDisplayConfigBufferSizes failed: {result}")

        paths = (DISPLAYCONFIG_PATH_INFO * pc.value)()
        modes = (DISPLAYCONFIG_MODE_INFO * mc.value)()

        result = QueryDisplayConfig(0x02, ctypes.byref(pc), paths, ctypes.byref(mc), modes, None)
        if result != 0:
            raise Exception(f"QueryDisplayConfig failed: {result}")

        return {
            'paths': [self._dump_path(paths[i]) for i in range(pc.value)],
            'modes': [self._dump_mode(modes[i]) for i in range(mc.value)]
        }

    def apply(self, cfg, monitors: list[dict[str, Any]] | None = None):
        """Apply a saved display configuration using a two-phase approach.

        Phase 1 — Set the source-to-target topology via SDC_TOPOLOGY_SUPPLIED
        using fresh adapter LUIDs (avoids stale serialized data).

        Phase 2 — Restore the saved source modes, rotation, scaling and refresh
        rates on the fresh configuration, then verify the resulting settings.
        """
        _INVALID = 0xFFFFFFFF

        # --- Get current adapter LUID (query ALL paths, not just active,
        # so transiently-inactive targets like KVM-switched monitors are visible) ---
        # QDC_ALL_PATHS = 0x01
        pc0, mc0 = c_uint32(), c_uint32()
        r = GetDisplayConfigBufferSizes(0x01, ctypes.byref(pc0), ctypes.byref(mc0))
        if r != 0:
            _log.error('GetDisplayConfigBufferSizes failed: %d', r)
            return r
        cur_p = (DISPLAYCONFIG_PATH_INFO * pc0.value)()
        cur_m = (DISPLAYCONFIG_MODE_INFO * mc0.value)()
        r = QueryDisplayConfig(0x01, ctypes.byref(pc0), cur_p, ctypes.byref(mc0), cur_m, None)
        if r != 0:
            _log.error('QueryDisplayConfig failed: %d', r)
            return r

        cur_info = {}
        cur_by_device_path = {}
        cur_by_edid = {}

        try:
            from display_presets.displays import _get_monitor_device_info
        except ImportError:
            _get_monitor_device_info = None

        for i in range(pc0.value):
            tid = cur_p[i].targetInfo.id
            adapter_id = {
                'LowPart': int(cur_p[i].targetInfo.adapterId.LowPart),
                'HighPart': int(cur_p[i].targetInfo.adapterId.HighPart),
            }
            device_info = {}
            if _get_monitor_device_info is not None:
                try:
                    device_info = _get_monitor_device_info(adapter_id, int(tid))
                except Exception:
                    device_info = {}

            source_available = cur_p[i].sourceInfo.modeInfoIdx != _INVALID
            score = (
                8 if cur_p[i].flags & 1 else 0,
                4 if cur_p[i].targetInfo.targetAvailable else 0,
                2 if cur_p[i].targetInfo.statusFlags else 0,
                1 if source_available else 0,
            )
            row = {
                'target_id': int(tid),
                'luid_lo': cur_p[i].sourceInfo.adapterId.LowPart,
                'luid_hi': cur_p[i].sourceInfo.adapterId.HighPart,
                'out_tech': cur_p[i].targetInfo.outputTechnology,
                'score': score,
                'device_path': _normalize_device_path(device_info.get('devicePath')),
                'edid_key': _edid_key(device_info),
                'name': device_info.get('name'),
            }
            if tid not in cur_info or score > cur_info[tid]['score']:
                cur_info[tid] = row

            device_path = row['device_path']
            if device_path and (
                device_path not in cur_by_device_path
                or score > cur_by_device_path[device_path]['score']
            ):
                cur_by_device_path[device_path] = row

            edid_key = row['edid_key']
            if edid_key:
                cur_by_edid.setdefault(edid_key, []).append(row)

        default_ci = next(iter(cur_info.values())) if cur_info else {
            'luid_lo': 0, 'luid_hi': 0, 'out_tech': 0,
        }

        saved = cfg['paths']
        target_id_map = {}
        for i, sp in enumerate(saved):
            saved_tid = sp['targetInfo']['id']
            if saved_tid in cur_info:
                target_id_map[saved_tid] = saved_tid
                continue

            monitor = _monitor_for_saved_path(monitors, i)
            identity = _path_monitor_identity(sp) or monitor
            resolved = _resolve_current_target(identity, cur_by_device_path, cur_by_edid)
            if resolved is None:
                continue

            target_id_map[saved_tid] = resolved['target_id']
            _log.warning(
                'Remapping saved target id %d to current target id %d for %s',
                saved_tid,
                resolved['target_id'],
                identity.get('name') or resolved.get('name') or 'display',
            )

        # --- Extract saved source modes and per-target settings ---
        desired = {}
        for p in cfg['paths']:
            saved_tid = p['targetInfo']['id']
            tid = target_id_map.get(saved_tid, saved_tid)
            si = p['sourceInfo']['modeInfoIdx']
            if si != _INVALID and si < len(cfg['modes']):
                m = cfg['modes'][si]
                if m.get('infoType') == 1 and 'sourceMode' in m:
                    sm = m['sourceMode']
                    numerator, denominator, scanline = _path_signal_settings(p, cfg['modes'])
                    desired[tid] = {
                        'source': sm,
                        'rotation': p['targetInfo']['rotation'],
                        'scaling': p['targetInfo']['scaling'],
                        'refresh': (numerator, denominator),
                        'scanline': scanline,
                        'signal': _path_target_signal(p, cfg['modes']),
                        'nominal': p.get('refreshRateIsNominal', False),
                    }

        _log.debug('apply: desired display settings for %d targets: %s', len(desired), desired)

        # --- Pre-flight: every saved target id must be reachable on this adapter ---
        missing = [
            p['targetInfo']['id'] for p in cfg['paths']
            if target_id_map.get(p['targetInfo']['id'], p['targetInfo']['id']) not in cur_info
        ]
        if missing:
            _log.error('Saved targets not present on current adapter: %s', missing)
            missing_ids = ', '.join(str(t) for t in missing)
            target_label = 'target ids' if len(missing) > 1 else 'target id'
            raise Exception(
                'Preset references display(s) not currently connected '
                f'({target_label}: {missing_ids}). '
                'Reconnect the display or save a new preset with the current setup.'
            )

        # --- Phase 1: Set topology ---
        n = len(saved)
        tp = (DISPLAYCONFIG_PATH_INFO * n)()

        for i, sp in enumerate(saved):
            tid = target_id_map.get(sp['targetInfo']['id'], sp['targetInfo']['id'])
            ci = cur_info.get(tid, default_ci)

            tp[i].sourceInfo.adapterId.LowPart = ci['luid_lo']
            tp[i].sourceInfo.adapterId.HighPart = ci['luid_hi']
            tp[i].sourceInfo.id = sp['sourceInfo']['id']
            tp[i].sourceInfo.modeInfoIdx = _INVALID
            tp[i].sourceInfo.statusFlags = 0

            tp[i].targetInfo.adapterId.LowPart = ci['luid_lo']
            tp[i].targetInfo.adapterId.HighPart = ci['luid_hi']
            tp[i].targetInfo.id = tid
            tp[i].targetInfo.modeInfoIdx = _INVALID
            tp[i].targetInfo.outputTechnology = ci['out_tech']
            tp[i].targetInfo.rotation = 1       # DISPLAYCONFIG_ROTATION_IDENTITY
            tp[i].targetInfo.scaling = 128       # DISPLAYCONFIG_SCALING_PREFERRED
            tp[i].targetInfo.refreshRate.Numerator = 0
            tp[i].targetInfo.refreshRate.Denominator = 0
            tp[i].targetInfo.scanLineOrdering = 0
            tp[i].targetInfo.targetAvailable = True
            tp[i].targetInfo.statusFlags = 0

            tp[i].flags = 1  # DISPLAYCONFIG_PATH_ACTIVE

        for i in range(n):
            _log.debug(
                '  topo[%d]: src(id=%d) tgt(id=%d tech=%d)',
                i, tp[i].sourceInfo.id, tp[i].targetInfo.id,
                tp[i].targetInfo.outputTechnology,
            )

        # SDC_APPLY | SDC_TOPOLOGY_SUPPLIED | SDC_ALLOW_PATH_ORDER_CHANGES
        # NOTE: SDC_TOPOLOGY_SUPPLIED must NOT be combined with SDC_ALLOW_CHANGES
        # or SDC_SAVE_TO_DATABASE — those are only valid with SDC_USE_SUPPLIED_DISPLAY_CONFIG.
        r1 = SetDisplayConfig(n, tp, 0, None, 0x80 | 0x10 | 0x2000)
        _log.info('Phase 1 (topology): %d paths, code=%d', n, r1)

        if r1 != 0:
            _log.error('Phase 1 failed: code=%d — cannot set topology', r1)
            return r1

        # --- Phase 2: Restore modes and target settings on fresh config ---
        if not desired:
            _log.info('No source mode data in saved config; topology applied, done')
            return 0

        pc2, mc2 = c_uint32(), c_uint32()
        result = GetDisplayConfigBufferSizes(0x02, ctypes.byref(pc2), ctypes.byref(mc2))
        if result != 0:
            _log.error('Phase 2 GetDisplayConfigBufferSizes failed: %d', result)
            return result
        fp = (DISPLAYCONFIG_PATH_INFO * pc2.value)()
        fm = (DISPLAYCONFIG_MODE_INFO * mc2.value)()
        result = QueryDisplayConfig(0x02, ctypes.byref(pc2), fp, ctypes.byref(mc2), fm, None)
        if result != 0:
            _log.error('Phase 2 QueryDisplayConfig failed: %d', result)
            return result

        _log.debug('Phase 2: fresh config has %d paths, %d modes', pc2.value, mc2.value)

        changed = False
        changed_source_modes = set()
        seen_targets = set()
        for i in range(pc2.value):
            tid = fp[i].targetInfo.id
            if tid not in desired:
                continue
            seen_targets.add(tid)
            source = desired[tid]['source']
            si = fp[i].sourceInfo.modeInfoIdx
            if si == _INVALID or si >= mc2.value or fm[si].infoType != 1:
                raise RuntimeError(f'Windows did not restore a source mode for display {tid}')
            sm = fm[si].modeInfo.sourceMode
            for field in ('width', 'height', 'pixelFormat'):
                if getattr(sm, field) != source[field]:
                    _log.debug('  tgt %d: %s %d -> %d',
                               tid, field, getattr(sm, field), source[field])
                    setattr(sm, field, source[field])
                    changed_source_modes.add(si)
                    changed = True
            position = source['position']
            if sm.position.x != position['x'] or sm.position.y != position['y']:
                _log.debug(
                    '  tgt %d: pos (%d,%d) -> (%d,%d)',
                    tid, sm.position.x, sm.position.y, position['x'], position['y'],
                )
                sm.position.x = position['x']
                sm.position.y = position['y']
                changed = True

        if seen_targets != set(desired):
            raise RuntimeError('Windows did not restore all preset displays')

        # Restore each clone target independently while preserving its fresh identity.
        additional_modes = []
        for i in range(pc2.value):
            target = fp[i].targetInfo
            if target.id not in desired:
                continue
            d = desired[target.id]
            current_rate = (target.refreshRate.Numerator, target.refreshRate.Denominator)
            scanline = target.scanLineOrdering
            ti = target.modeInfoIdx
            current_signal = None
            if ti != _INVALID and ti < mc2.value and fm[ti].infoType == 2:
                signal = fm[ti].modeInfo.targetMode.targetVideoSignalInfo
                current_rate = (signal.vSyncFreq.Numerator, signal.vSyncFreq.Denominator)
                scanline = signal.scanLineOrdering
                current_signal = self._dump_mode(fm[ti])['targetMode']['targetVideoSignalInfo']
            rate_specified = d['refresh'][0] > 0 and d['refresh'][1] > 0
            if (fp[i].sourceInfo.modeInfoIdx in changed_source_modes
                    or target.rotation != d['rotation']
                    or (d['scaling'] != 128 and target.scaling != d['scaling'])
                    or (rate_specified and not _same_refresh_rate(
                        current_rate, d['refresh'], d['nominal']))
                    or (d['signal'] is not None
                        and not _same_target_signal(current_signal, d['signal']))
                    or (d['scanline'] != 0 and scanline != d['scanline'])):
                target.rotation = d['rotation']
                target.scaling = d['scaling']
                target.refreshRate.Numerator, target.refreshRate.Denominator = d['refresh']
                target.scanLineOrdering = d['scanline'] if rate_specified else 0
                if d['signal'] is not None:
                    if current_signal is None:
                        mode = DISPLAYCONFIG_MODE_INFO()
                        mode.infoType = 2
                        mode.id = target.id
                        mode.adapterId = target.adapterId
                        target.modeInfoIdx = mc2.value + len(additional_modes)
                        additional_modes.append(mode)
                    else:
                        mode = fm[ti]
                    signal = mode.modeInfo.targetMode.targetVideoSignalInfo
                    for field, value in d['signal'].items():
                        if isinstance(value, dict):
                            for member, number in value.items():
                                setattr(getattr(signal, field), member, number)
                        else:
                            setattr(signal, field, value)
                else:
                    # Editor changes require a new timing selected by Windows.
                    target.modeInfoIdx = _INVALID
                changed = True

        if not changed:
            _log.info('Display settings already match saved preset; done')
            return 0

        # SDC_APPLY | SDC_USE_SUPPLIED_DISPLAY_CONFIG; reject unsupported modes.
        if additional_modes:
            fm = (DISPLAYCONFIG_MODE_INFO * (mc2.value + len(additional_modes)))(
                *fm[:mc2.value], *additional_modes,
            )
            mc2.value = len(fm)
        r2 = SetDisplayConfig(pc2.value, fp, mc2.value, fm, 0x80 | 0x20)
        _log.info('Phase 2 (display settings): code=%d', r2)

        if r2 != 0:
            _log.warning('Phase 2 failed but topology was set in Phase 1')
            return r2

        actual = self.get_current()
        verified = set()
        for path in actual['paths']:
            tid = path['targetInfo']['id']
            if tid not in desired:
                continue
            d = desired[tid]
            si = path['sourceInfo']['modeInfoIdx']
            if si >= len(actual['modes']) or actual['modes'][si].get('infoType') != 1:
                raise RuntimeError(f'Windows did not restore a source mode for display {tid}')
            source = actual['modes'][si]['sourceMode']
            rate = _path_signal_settings(path, actual['modes'])[:2]
            if (source != d['source']
                    or path['targetInfo']['rotation'] != d['rotation']
                    or (d['signal'] is not None and not _same_target_signal(
                        _path_target_signal(path, actual['modes']), d['signal']))
                    or (d['refresh'][0] > 0 and d['refresh'][1] > 0
                        and not _same_refresh_rate(rate, d['refresh'], d['nominal']))):
                raise RuntimeError(f'Windows did not restore the saved settings for display {tid}')
            verified.add(tid)
        if verified != set(desired):
            raise RuntimeError('Windows did not restore all preset displays')

        return 0

    def _dump_path(self, p):
        path = {
            'sourceInfo': {
                'adapterId': {'LowPart': int(p.sourceInfo.adapterId.LowPart),
                             'HighPart': int(p.sourceInfo.adapterId.HighPart)},
                'id': int(p.sourceInfo.id),
                'modeInfoIdx': int(p.sourceInfo.modeInfoIdx),
                'statusFlags': int(p.sourceInfo.statusFlags)
            },
            'targetInfo': {
                'adapterId': {'LowPart': int(p.targetInfo.adapterId.LowPart),
                             'HighPart': int(p.targetInfo.adapterId.HighPart)},
                'id': int(p.targetInfo.id),
                'modeInfoIdx': int(p.targetInfo.modeInfoIdx),
                'outputTechnology': int(p.targetInfo.outputTechnology),
                'rotation': int(p.targetInfo.rotation),
                'scaling': int(p.targetInfo.scaling),
                'refreshRate': {'Numerator': int(p.targetInfo.refreshRate.Numerator),
                               'Denominator': int(p.targetInfo.refreshRate.Denominator)},
                'scanLineOrdering': int(p.targetInfo.scanLineOrdering),
                'targetAvailable': bool(p.targetInfo.targetAvailable),
                'statusFlags': int(p.targetInfo.statusFlags)
            },
            'flags': int(p.flags)
        }
        identity = self._get_path_monitor_identity(path['targetInfo'])
        if identity:
            path['monitorIdentity'] = identity
        return path

    def _get_path_monitor_identity(self, target_info: dict[str, Any]) -> dict[str, Any]:
        try:
            from display_presets.displays import _get_monitor_device_info
        except ImportError:
            return {}

        adapter_id = target_info.get('adapterId')
        target_id = target_info.get('id')
        if not isinstance(adapter_id, dict) or not isinstance(target_id, int):
            return {}

        try:
            info = _get_monitor_device_info(adapter_id, target_id)
        except Exception:
            return {}

        identity = {
            'name': info.get('name'),
            'devicePath': info.get('devicePath'),
            'edidManufactureId': info.get('edidManufactureId', 0),
            'edidProductCodeId': info.get('edidProductCodeId', 0),
        }
        return {
            key: value for key, value in identity.items()
            if value not in (None, '', 0)
        }

    def _dump_mode(self, m):
        d = {
            'infoType': int(m.infoType),
            'id': int(m.id),
            'adapterId': {'LowPart': int(m.adapterId.LowPart), 'HighPart': int(m.adapterId.HighPart)}
        }

        if m.infoType == 1:  # source
            d['sourceMode'] = {
                'width': int(m.modeInfo.sourceMode.width),
                'height': int(m.modeInfo.sourceMode.height),
                'pixelFormat': int(m.modeInfo.sourceMode.pixelFormat),
                'position': {'x': int(m.modeInfo.sourceMode.position.x),
                            'y': int(m.modeInfo.sourceMode.position.y)}
            }
        elif m.infoType == 2:  # target
            v = m.modeInfo.targetMode.targetVideoSignalInfo
            d['targetMode'] = {
                'targetVideoSignalInfo': {
                    'pixelRate': int(v.pixelRate),
                    'hSyncFreq': {'Numerator': int(v.hSyncFreq.Numerator), 'Denominator': int(v.hSyncFreq.Denominator)},
                    'vSyncFreq': {'Numerator': int(v.vSyncFreq.Numerator), 'Denominator': int(v.vSyncFreq.Denominator)},
                    'activeSize': {'cx': int(v.activeSize.cx), 'cy': int(v.activeSize.cy)},
                    'totalSize': {'cx': int(v.totalSize.cx), 'cy': int(v.totalSize.cy)},
                    'videoStandard': int(v.videoStandard),
                    'scanLineOrdering': int(v.scanLineOrdering)
                }
            }
        elif m.infoType == 3:  # desktop
            di = m.modeInfo.desktopImageInfo
            d['desktopImageInfo'] = {
                'PathSourceSize': {'x': int(di.PathSourceSize.x), 'y': int(di.PathSourceSize.y)},
                'DesktopImageRegion': {'left': int(di.DesktopImageRegion.left), 'top': int(di.DesktopImageRegion.top),
                                      'right': int(di.DesktopImageRegion.right), 'bottom': int(di.DesktopImageRegion.bottom)},
                'DesktopImageClip': {'left': int(di.DesktopImageClip.left), 'top': int(di.DesktopImageClip.top),
                                    'right': int(di.DesktopImageClip.right), 'bottom': int(di.DesktopImageClip.bottom)}
            }
        return d

    # SDC_APPLY | topology flag — no paths/modes needed, Windows picks best fit
    _TOPOLOGY_FLAGS = {
        'extend':   0x80 | 0x04,
        'clone':    0x80 | 0x02,
        'internal': 0x80 | 0x01,
        'external': 0x80 | 0x08,
    }

    def rebuild_config_for_monitors(self, config: dict, monitors: list) -> dict:
        """
        Produce a modified copy of `config` whose source-mode assignments reflect
        the topology encoded in `monitors` (the edited monitor list from the frontend).

        Monitors that share the same (x, y, width, height) are treated as a clone
        group and will be assigned the same source mode (and the same sourceInfo.id).
        Monitors with unique positions are extended and receive independent sources.

        Monitors are matched to path indices in this order:
          1. By monitor devicePath (stable identity — survives USB replug and
             driver re-enumeration that shifts path ordering).
          2. By id='monitor_N' where N is the path index (legacy fallback for
             presets saved before devicePath was captured).
        """
        import copy

        cfg = copy.deepcopy(config)
        paths = cfg['paths']
        modes = cfg['modes']

        _INVALID = 0xFFFFFFFF

        # Resolve the current devicePath for every path index in the config,
        # so we can match incoming monitors by stable identity first.
        try:
            from display_presets.displays import _get_monitor_device_info
        except ImportError:
            _get_monitor_device_info = None

        path_device_paths: dict = {}
        if _get_monitor_device_info is not None:
            for i, p in enumerate(paths):
                tgt = p.get('targetInfo') or {}
                adapter = tgt.get('adapterId')
                target_id = tgt.get('id')
                if not isinstance(adapter, dict) or not isinstance(target_id, int):
                    continue
                try:
                    info = _get_monitor_device_info(adapter, target_id)
                    dp = info.get('devicePath')
                    if dp:
                        path_device_paths[dp] = i
                except Exception:
                    pass

        # Build path_idx -> monitor map. Prefer devicePath; fall back to monitor_N.
        idx_to_mon = {}
        claimed_idxs: set = set()
        for m in monitors:
            dp = m.get('devicePath') if isinstance(m, dict) else None
            idx = None
            if isinstance(dp, str) and dp and dp in path_device_paths:
                candidate = path_device_paths[dp]
                if candidate not in claimed_idxs:
                    idx = candidate
            if idx is None:
                mid = m.get('id', '')
                if isinstance(mid, str) and mid.startswith('monitor_'):
                    try:
                        candidate = int(mid.split('_', 1)[1])
                        if 0 <= candidate < len(paths) and candidate not in claimed_idxs:
                            idx = candidate
                    except (ValueError, IndexError):
                        pass
            if idx is not None:
                idx_to_mon[idx] = m
                claimed_idxs.add(idx)

        if not idx_to_mon:
            return cfg

        for idx, monitor in idx_to_mon.items():
            path = paths[idx]
            target = path['targetInfo']
            numerator, denominator, scanline = _path_signal_settings(path, modes)
            rotation = monitor.get('rotation', (target['rotation'] - 1) * 90) // 90 + 1
            timing_changed = rotation != target['rotation']
            si = path['sourceInfo']['modeInfoIdx']
            if si != _INVALID and si < len(modes) and modes[si].get('infoType') == 1:
                source = modes[si]['sourceMode']
                timing_changed |= (source['width'], source['height']) != (
                    int(monitor['width']), int(monitor['height']),
                )
            if ('refreshRate' in monitor
                    and (timing_changed or not denominator
                         or monitor['refreshRate'] != round(numerator / denominator))):
                rate = Fraction(str(monitor['refreshRate']))
                numerator, denominator = rate.numerator, rate.denominator
                path['refreshRateIsNominal'] = denominator == 1
                timing_changed = True
            target['rotation'] = rotation
            target['refreshRate'] = {'Numerator': numerator, 'Denominator': denominator}
            target['scanLineOrdering'] = scanline
            if timing_changed:
                target['modeInfoIdx'] = _INVALID

        # Group path indices by the new position key (clone groups share a position)
        pos_to_paths = {}
        for idx, m in idx_to_mon.items():
            key = (int(m['x']), int(m['y']), int(m['width']), int(m['height']))
            pos_to_paths.setdefault(key, []).append(idx)
        for k in pos_to_paths:
            pos_to_paths[k].sort()

        # Process groups left-to-right/top-to-bottom so the leftmost group gets
        # priority when claiming an original source mode slot.
        claimed = {}          # orig_mode_idx -> leader path_idx that owns it
        valid_src_ids = [p['sourceInfo']['id'] for p in paths if p['sourceInfo']['id'] != _INVALID]
        next_src_id = (max(valid_src_ids) + 1) if valid_src_ids else 1

        for pos_key in sorted(pos_to_paths.keys()):
            x, y, w, h = pos_key
            path_indices = pos_to_paths[pos_key]
            leader = path_indices[0]

            # Find a valid source mode index to use as the base for this group.
            # Prefer the leader's own original mode, fall back to any follower's.
            orig_mode_idx = paths[leader]['sourceInfo']['modeInfoIdx']
            if orig_mode_idx == _INVALID or orig_mode_idx >= len(modes):
                orig_mode_idx = _INVALID
                for pi in path_indices[1:]:
                    alt = paths[pi]['sourceInfo']['modeInfoIdx']
                    if alt != _INVALID and alt < len(modes):
                        orig_mode_idx = alt
                        break

            if orig_mode_idx == _INVALID:
                continue

            if orig_mode_idx not in claimed:
                # Claim this mode slot for our group
                actual_mode_idx = orig_mode_idx
                claimed[orig_mode_idx] = leader
                leader_src_id = paths[leader]['sourceInfo']['id']
            else:
                # Slot already taken by another group (split case): create a new one
                new_mode = copy.deepcopy(modes[orig_mode_idx])
                leader_src_id = next_src_id
                next_src_id += 1
                new_mode['id'] = leader_src_id
                actual_mode_idx = len(modes)
                modes.append(new_mode)
                claimed[actual_mode_idx] = leader
                paths[leader]['sourceInfo']['id'] = leader_src_id

            # Update source mode position and dimensions to match the edited layout
            mode = modes[actual_mode_idx]
            if mode.get('infoType') == 1:
                mode['sourceMode']['position']['x'] = x
                mode['sourceMode']['position']['y'] = y
                mode['sourceMode']['width'] = w
                mode['sourceMode']['height'] = h

            # Point all paths in this group at the same source
            for pi in path_indices:
                paths[pi]['sourceInfo']['id'] = leader_src_id
                paths[pi]['sourceInfo']['modeInfoIdx'] = actual_mode_idx

        return cfg

    def set_topology(self, topology: str) -> dict:
        flag = self._TOPOLOGY_FLAGS.get(topology)
        if flag is None:
            raise ValueError(f'Unknown topology: {topology}')
        result = SetDisplayConfig(0, None, 0, None, flag)
        if result != 0:
            raise Exception(f'SetDisplayConfig topology={topology} failed: {result}')
        return self.get_current()
