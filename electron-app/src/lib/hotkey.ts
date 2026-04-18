const shiftedToBase: Record<string, string> = {
  '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
  '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
  '_': '-', '+': '=', ':': ';', '"': "'", '<': ',',
  '>': '.', '?': '/', '~': '`', '|': '\\',
};

// Keys that can be used as a standalone global hotkey without modifiers.
// Must match STANDALONE_KEYS in electron/hotkey.ts.
const STANDALONE_KEYS = new Set<string>([
  ...Array.from({ length: 24 }, (_, i) => `F${i + 1}`),
  'MediaPlayPause', 'MediaStop', 'MediaTrackNext', 'MediaTrackPrevious',
  'AudioVolumeUp', 'AudioVolumeDown', 'AudioVolumeMute',
]);

export interface KeyComboInput {
  key: string;
  ctrlKey: boolean;
  altKey: boolean;
  shiftKey: boolean;
  metaKey: boolean;
}

// Convert a browser KeyboardEvent-like object to a stored hotkey combo
// (e.g. "Ctrl+Alt+Shift+8"). Returns null if the combo is invalid or has
// no non-modifier key.
export function formatKeyCombo(e: KeyComboInput): string | null {
  const parts: string[] = [];
  if (e.ctrlKey) parts.push('Ctrl');
  if (e.altKey) parts.push('Alt');
  if (e.shiftKey) parts.push('Shift');
  if (e.metaKey) parts.push('Win');

  let key = e.key;
  if (['Control', 'Alt', 'Shift', 'Meta'].includes(key)) return null;

  if (e.shiftKey && shiftedToBase[key]) {
    key = shiftedToBase[key];
  }

  if (key.length === 1) {
    parts.push(key.toUpperCase());
  } else {
    parts.push(key);
  }

  const hasModifier = parts.length > 1;
  if (!hasModifier && !STANDALONE_KEYS.has(key)) return null;

  return parts.join('+');
}
