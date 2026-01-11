import ctypes
from ctypes import wintypes
import threading
from PyQt6.QtCore import QObject, pyqtSignal


# Windows API constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312


class HotkeyManager(QObject):
    hotkey_pressed = pyqtSignal(int)  # Emits hotkey ID

    def __init__(self):
        super().__init__()
        self.registered = {}
        self.next_id = 1
        self.running = False

    def register(self, modifiers, key, callback_id):
        """
        Register a hotkey
        modifiers: combination of MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN
        key: Virtual key code (e.g., ord('A') for A)
        callback_id: unique ID for this hotkey
        """
        try:
            user32 = ctypes.windll.user32
            result = user32.RegisterHotKey(None, callback_id, modifiers | MOD_NOREPEAT, key)
            if result:
                self.registered[callback_id] = (modifiers, key)
                return True
            return False
        except Exception as e:
            print(f"Failed to register hotkey: {e}")
            return False

    def unregister(self, callback_id):
        """Unregister a hotkey"""
        if callback_id in self.registered:
            try:
                user32 = ctypes.windll.user32
                user32.UnregisterHotKey(None, callback_id)
                del self.registered[callback_id]
            except:
                pass

    def unregister_all(self):
        """Unregister all hotkeys"""
        for callback_id in list(self.registered.keys()):
            self.unregister(callback_id)

    def start_listening(self):
        """Start listening for hotkeys in background thread"""
        if self.running:
            return

        self.running = True
        threading.Thread(target=self._message_loop, daemon=True).start()

    def stop_listening(self):
        """Stop listening for hotkeys"""
        self.running = False
        self.unregister_all()

    def _message_loop(self):
        """Windows message loop for hotkeys"""
        try:
            user32 = ctypes.windll.user32

            msg = wintypes.MSG()
            while self.running:
                result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if result == 0 or result == -1:
                    break

                if msg.message == WM_HOTKEY:
                    hotkey_id = msg.wParam
                    self.hotkey_pressed.emit(hotkey_id)

                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        except Exception as e:
            print(f"Hotkey listener error: {e}")


def parse_hotkey_string(hotkey_str):
    """
    Parse hotkey string like "Ctrl+Shift+A" to modifiers and key code
    Returns (modifiers, keycode) or None if invalid
    """
    if not hotkey_str:
        return None

    parts = [p.strip() for p in hotkey_str.split('+')]
    if len(parts) < 2:
        return None

    modifiers = 0
    key = None

    for part in parts:
        part_upper = part.upper()
        if part_upper == 'CTRL' or part_upper == 'CONTROL':
            modifiers |= MOD_CONTROL
        elif part_upper == 'ALT':
            modifiers |= MOD_ALT
        elif part_upper == 'SHIFT':
            modifiers |= MOD_SHIFT
        elif part_upper == 'WIN':
            modifiers |= MOD_WIN
        elif len(part) == 1:
            key = ord(part.upper())
        else:
            # Function keys, etc
            vk_map = {
                'F1': 0x70, 'F2': 0x71, 'F3': 0x72, 'F4': 0x73,
                'F5': 0x74, 'F6': 0x75, 'F7': 0x76, 'F8': 0x77,
                'F9': 0x78, 'F10': 0x79, 'F11': 0x7A, 'F12': 0x7B,
            }
            key = vk_map.get(part_upper)

    if key is None or modifiers == 0:
        return None

    return (modifiers, key)


def format_hotkey(modifiers, key):
    """Convert modifiers and key code back to string"""
    parts = []

    if modifiers & MOD_CONTROL:
        parts.append('Ctrl')
    if modifiers & MOD_ALT:
        parts.append('Alt')
    if modifiers & MOD_SHIFT:
        parts.append('Shift')
    if modifiers & MOD_WIN:
        parts.append('Win')

    # Try to convert key code to character
    if 0x41 <= key <= 0x5A:  # A-Z
        parts.append(chr(key))
    elif 0x70 <= key <= 0x7B:  # F1-F12
        parts.append(f'F{key - 0x6F}')
    else:
        parts.append(f'Key{key}')

    return '+'.join(parts)
