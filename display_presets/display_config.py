import ctypes
import json
from ctypes import wintypes, Structure, POINTER, c_uint32, c_int32, c_uint64, c_bool

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

    def apply(self, cfg):
        """Apply a saved display configuration using a two-phase approach.

        Phase 1 — Set the source-to-target topology via SDC_TOPOLOGY_SUPPLIED
        using fresh adapter LUIDs (avoids stale serialized data).

        Phase 2 — Query the resulting fresh config from Windows, adjust source
        positions to match the saved preset, and apply back.
        """
        _INVALID = 0xFFFFFFFF

        # --- Extract desired source positions from saved config ---
        desired = {}  # target_id -> {x, y}
        for p in cfg['paths']:
            tid = p['targetInfo']['id']
            si = p['sourceInfo']['modeInfoIdx']
            if si != _INVALID and si < len(cfg['modes']):
                m = cfg['modes'][si]
                if m.get('infoType') == 1 and 'sourceMode' in m:
                    sm = m['sourceMode']
                    desired[tid] = {'x': sm['position']['x'], 'y': sm['position']['y']}

        _log.debug('apply: desired positions for %d targets: %s', len(desired), desired)

        # --- Get current adapter LUID ---
        pc0, mc0 = c_uint32(), c_uint32()
        r = GetDisplayConfigBufferSizes(0x02, ctypes.byref(pc0), ctypes.byref(mc0))
        if r != 0:
            _log.error('GetDisplayConfigBufferSizes failed: %d', r)
            return r
        cur_p = (DISPLAYCONFIG_PATH_INFO * pc0.value)()
        cur_m = (DISPLAYCONFIG_MODE_INFO * mc0.value)()
        r = QueryDisplayConfig(0x02, ctypes.byref(pc0), cur_p, ctypes.byref(mc0), cur_m, None)
        if r != 0:
            _log.error('QueryDisplayConfig failed: %d', r)
            return r

        cur_info = {}
        for i in range(pc0.value):
            tid = cur_p[i].targetInfo.id
            cur_info[tid] = {
                'luid_lo': cur_p[i].sourceInfo.adapterId.LowPart,
                'luid_hi': cur_p[i].sourceInfo.adapterId.HighPart,
                'out_tech': cur_p[i].targetInfo.outputTechnology,
            }

        default_ci = next(iter(cur_info.values())) if cur_info else {
            'luid_lo': 0, 'luid_hi': 0, 'out_tech': 0,
        }

        # --- Phase 1: Set topology ---
        saved = cfg['paths']
        n = len(saved)
        tp = (DISPLAYCONFIG_PATH_INFO * n)()

        for i, sp in enumerate(saved):
            tid = sp['targetInfo']['id']
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

        # --- Phase 2: Adjust source positions on fresh config ---
        if not desired:
            _log.info('No position data in saved config; topology applied, done')
            return 0

        pc2, mc2 = c_uint32(), c_uint32()
        GetDisplayConfigBufferSizes(0x02, ctypes.byref(pc2), ctypes.byref(mc2))
        fp = (DISPLAYCONFIG_PATH_INFO * pc2.value)()
        fm = (DISPLAYCONFIG_MODE_INFO * mc2.value)()
        QueryDisplayConfig(0x02, ctypes.byref(pc2), fp, ctypes.byref(mc2), fm, None)

        _log.debug('Phase 2: fresh config has %d paths, %d modes', pc2.value, mc2.value)

        changed = False
        for i in range(pc2.value):
            tid = fp[i].targetInfo.id
            if tid not in desired:
                continue
            d = desired[tid]
            si = fp[i].sourceInfo.modeInfoIdx
            if si == _INVALID or si >= mc2.value or fm[si].infoType != 1:
                continue
            sm = fm[si].modeInfo.sourceMode
            if sm.position.x != d['x'] or sm.position.y != d['y']:
                _log.debug(
                    '  tgt %d: pos (%d,%d) -> (%d,%d)',
                    tid, sm.position.x, sm.position.y, d['x'], d['y'],
                )
                sm.position.x = d['x']
                sm.position.y = d['y']
                changed = True

        if not changed:
            _log.info('Positions already match saved preset; done')
            return 0

        # SDC_APPLY | SDC_USE_SUPPLIED_DISPLAY_CONFIG | SDC_ALLOW_CHANGES
        r2 = SetDisplayConfig(pc2.value, fp, mc2.value, fm, 0x80 | 0x20 | 0x400)
        _log.info('Phase 2 (positions): code=%d', r2)

        if r2 != 0:
            _log.warning('Phase 2 failed but topology was set in Phase 1')

        return 0

    def _dump_path(self, p):
        return {
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

        Each monitor must have id='monitor_N' where N is the corresponding path
        index in config['paths'] — this is the convention used by get_current_displays().
        """
        import copy

        cfg = copy.deepcopy(config)
        paths = cfg['paths']
        modes = cfg['modes']

        _INVALID = 0xFFFFFFFF

        # Build path_idx -> monitor map
        idx_to_mon = {}
        for m in monitors:
            mid = m.get('id', '')
            if isinstance(mid, str) and mid.startswith('monitor_'):
                try:
                    idx = int(mid.split('_', 1)[1])
                    if 0 <= idx < len(paths):
                        idx_to_mon[idx] = m
                except (ValueError, IndexError):
                    pass

        if not idx_to_mon:
            return cfg

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
