// Convert a hotkey combo captured from the renderer (e.g. "Ctrl+Alt+Shift+-")
// into an Electron accelerator string (e.g. "CommandOrControl+Alt+Shift+-").
// Returns null if the combo cannot be represented as a valid accelerator.
export function toAccelerator(combo: string): string | null {
  const parts = combo.split('+').filter((p) => p.length > 0);
  if (parts.length < 2) return null;

  const key = parts[parts.length - 1];
  const modifiers = parts.slice(0, -1).map((m) => {
    if (m === 'Ctrl') return 'CommandOrControl';
    if (m === 'Win') return 'Super';
    return m;
  });

  const keyMap: Record<string, string> = {
    ' ': 'Space',
    'ArrowUp': 'Up',
    'ArrowDown': 'Down',
    'ArrowLeft': 'Left',
    'ArrowRight': 'Right',
    'Escape': 'Esc',
  };
  let mapped = keyMap[key] ?? key;

  // Electron accelerators don't understand shifted characters like '*', '?', '!'.
  // Users must press an unshifted key; reject unsupported glyphs.
  const unsupported = new Set(['*', '?', '!', '@', '#', '$', '%', '^', '&', '(', ')', '_', '+', ':', '"', '<', '>', '|', '~']);
  if (mapped.length === 1 && unsupported.has(mapped)) return null;

  if (mapped.length === 1 && /[a-z]/.test(mapped)) mapped = mapped.toUpperCase();

  return [...modifiers, mapped].join('+');
}
