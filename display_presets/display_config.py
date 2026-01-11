import ctypes
from ctypes import wintypes, Structure, POINTER, c_uint32, c_int32, c_uint64, c_bool


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
        pc = len(cfg['paths'])
        mc = len(cfg['modes'])

        paths = (DISPLAYCONFIG_PATH_INFO * pc)()
        modes = (DISPLAYCONFIG_MODE_INFO * mc)()

        for i, p in enumerate(cfg['paths']):
            self._load_path(paths[i], p)

        for i, m in enumerate(cfg['modes']):
            self._load_mode(modes[i], m)

        # SDC_APPLY | SDC_USE_SUPPLIED_DISPLAY_CONFIG | SDC_ALLOW_CHANGES
        return SetDisplayConfig(pc, paths, mc, modes, 0x80 | 0x20 | 0x400)

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

    def _load_path(self, p, d):
        p.sourceInfo.adapterId.LowPart = d['sourceInfo']['adapterId']['LowPart']
        p.sourceInfo.adapterId.HighPart = d['sourceInfo']['adapterId']['HighPart']
        p.sourceInfo.id = d['sourceInfo']['id']
        p.sourceInfo.modeInfoIdx = d['sourceInfo']['modeInfoIdx']
        p.sourceInfo.statusFlags = d['sourceInfo']['statusFlags']

        p.targetInfo.adapterId.LowPart = d['targetInfo']['adapterId']['LowPart']
        p.targetInfo.adapterId.HighPart = d['targetInfo']['adapterId']['HighPart']
        p.targetInfo.id = d['targetInfo']['id']
        p.targetInfo.modeInfoIdx = d['targetInfo']['modeInfoIdx']
        p.targetInfo.outputTechnology = d['targetInfo']['outputTechnology']
        p.targetInfo.rotation = d['targetInfo']['rotation']
        p.targetInfo.scaling = d['targetInfo']['scaling']
        p.targetInfo.refreshRate.Numerator = d['targetInfo']['refreshRate']['Numerator']
        p.targetInfo.refreshRate.Denominator = d['targetInfo']['refreshRate']['Denominator']
        p.targetInfo.scanLineOrdering = d['targetInfo']['scanLineOrdering']
        p.targetInfo.targetAvailable = d['targetInfo']['targetAvailable']
        p.targetInfo.statusFlags = d['targetInfo']['statusFlags']
        p.flags = d['flags']

    def _load_mode(self, m, d):
        m.infoType = d['infoType']
        m.id = d['id']
        m.adapterId.LowPart = d['adapterId']['LowPart']
        m.adapterId.HighPart = d['adapterId']['HighPart']

        if m.infoType == 1 and 'sourceMode' in d:
            sm = d['sourceMode']
            m.modeInfo.sourceMode.width = sm['width']
            m.modeInfo.sourceMode.height = sm['height']
            m.modeInfo.sourceMode.pixelFormat = sm['pixelFormat']
            m.modeInfo.sourceMode.position.x = sm['position']['x']
            m.modeInfo.sourceMode.position.y = sm['position']['y']
        elif m.infoType == 2 and 'targetMode' in d:
            v = d['targetMode']['targetVideoSignalInfo']
            m.modeInfo.targetMode.targetVideoSignalInfo.pixelRate = v['pixelRate']
            m.modeInfo.targetMode.targetVideoSignalInfo.hSyncFreq.Numerator = v['hSyncFreq']['Numerator']
            m.modeInfo.targetMode.targetVideoSignalInfo.hSyncFreq.Denominator = v['hSyncFreq']['Denominator']
            m.modeInfo.targetMode.targetVideoSignalInfo.vSyncFreq.Numerator = v['vSyncFreq']['Numerator']
            m.modeInfo.targetMode.targetVideoSignalInfo.vSyncFreq.Denominator = v['vSyncFreq']['Denominator']
            m.modeInfo.targetMode.targetVideoSignalInfo.activeSize.cx = v['activeSize']['cx']
            m.modeInfo.targetMode.targetVideoSignalInfo.activeSize.cy = v['activeSize']['cy']
            m.modeInfo.targetMode.targetVideoSignalInfo.totalSize.cx = v['totalSize']['cx']
            m.modeInfo.targetMode.targetVideoSignalInfo.totalSize.cy = v['totalSize']['cy']
            m.modeInfo.targetMode.targetVideoSignalInfo.videoStandard = v['videoStandard']
            m.modeInfo.targetMode.targetVideoSignalInfo.scanLineOrdering = v['scanLineOrdering']
        elif m.infoType == 3 and 'desktopImageInfo' in d:
            di = d['desktopImageInfo']
            m.modeInfo.desktopImageInfo.PathSourceSize.x = di['PathSourceSize']['x']
            m.modeInfo.desktopImageInfo.PathSourceSize.y = di['PathSourceSize']['y']
            m.modeInfo.desktopImageInfo.DesktopImageRegion.left = di['DesktopImageRegion']['left']
            m.modeInfo.desktopImageInfo.DesktopImageRegion.top = di['DesktopImageRegion']['top']
            m.modeInfo.desktopImageInfo.DesktopImageRegion.right = di['DesktopImageRegion']['right']
            m.modeInfo.desktopImageInfo.DesktopImageRegion.bottom = di['DesktopImageRegion']['bottom']
            m.modeInfo.desktopImageInfo.DesktopImageClip.left = di['DesktopImageClip']['left']
            m.modeInfo.desktopImageInfo.DesktopImageClip.top = di['DesktopImageClip']['top']
            m.modeInfo.desktopImageInfo.DesktopImageClip.right = di['DesktopImageClip']['right']
            m.modeInfo.desktopImageInfo.DesktopImageClip.bottom = di['DesktopImageClip']['bottom']
