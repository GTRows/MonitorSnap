// Keys that Electron accepts as standalone accelerators (no modifier needed).
// F1-F24, media controls, and volume keys are dedicated and don't collide
// with normal typing.
const STANDALONE_KEYS = new Set<string>([
  ...Array.from({ length: 24 }, (_, i) => `F${i + 1}`),
  'MediaPlayPause', 'MediaStop', 'MediaNextTrack', 'MediaPreviousTrack',
  'VolumeUp', 'VolumeDown', 'VolumeMute',
]);

// Browser KeyboardEvent.key values that don't match Electron accelerator names.
const BROWSER_TO_ELECTRON_KEY: Record<string, string> = {
  ' ': 'Space',
  'ArrowUp': 'Up',
  'ArrowDown': 'Down',
  'ArrowLeft': 'Left',
  'ArrowRight': 'Right',
  'Escape': 'Esc',
  'MediaTrackNext': 'MediaNextTrack',
  'MediaTrackPrevious': 'MediaPreviousTrack',
  'AudioVolumeUp': 'VolumeUp',
  'AudioVolumeDown': 'VolumeDown',
  'AudioVolumeMute': 'VolumeMute',
};

// Convert a hotkey combo captured from the renderer (e.g. "Ctrl+Alt+Shift+-")
// into an Electron accelerator string (e.g. "CommandOrControl+Alt+Shift+-").
// Returns null if the combo cannot be represented as a valid accelerator.
export function toAccelerator(combo: string): string | null {
  const parts = combo.split('+').filter((p) => p.length > 0);
  if (parts.length === 0) return null;

  const key = parts[parts.length - 1];
  const modifiers = parts.slice(0, -1).map((m) => {
    if (m === 'Ctrl') return 'CommandOrControl';
    if (m === 'Win') return 'Super';
    return m;
  });

  let mapped = BROWSER_TO_ELECTRON_KEY[key] ?? key;

  // Electron accelerators don't understand shifted characters like '*', '?', '!'.
  // Users must press an unshifted key; reject unsupported glyphs.
  const unsupported = new Set(['*', '?', '!', '@', '#', '$', '%', '^', '&', '(', ')', '_', '+', ':', '"', '<', '>', '|', '~']);
  if (mapped.length === 1 && unsupported.has(mapped)) return null;

  if (mapped.length === 1 && /[a-z]/.test(mapped)) mapped = mapped.toUpperCase();

  if (modifiers.length === 0 && !STANDALONE_KEYS.has(mapped)) return null;

  return [...modifiers, mapped].join('+');
}
