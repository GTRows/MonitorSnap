import { describe, it, expect } from 'vitest';
import { toAccelerator } from './hotkey';

describe('toAccelerator', () => {
  it('maps Ctrl to CommandOrControl', () => {
    expect(toAccelerator('Ctrl+A')).toBe('CommandOrControl+A');
  });

  it('maps Win to Super', () => {
    expect(toAccelerator('Win+Shift+S')).toBe('Super+Shift+S');
  });

  it('uppercases single-character letter keys', () => {
    expect(toAccelerator('Ctrl+a')).toBe('CommandOrControl+A');
  });

  it('preserves digit keys', () => {
    expect(toAccelerator('Ctrl+Alt+Shift+8')).toBe('CommandOrControl+Alt+Shift+8');
  });

  it('preserves unshifted punctuation like minus', () => {
    expect(toAccelerator('Ctrl+Alt+Shift+-')).toBe('CommandOrControl+Alt+Shift+-');
  });

  it('rejects shifted glyphs that Electron cannot register', () => {
    expect(toAccelerator('Ctrl+Alt+Shift+*')).toBeNull();
    expect(toAccelerator('Ctrl+?')).toBeNull();
  });

  it('rejects combos with no modifier', () => {
    expect(toAccelerator('A')).toBeNull();
  });

  it('rejects empty input', () => {
    expect(toAccelerator('')).toBeNull();
  });

  it('maps ArrowUp to Up', () => {
    expect(toAccelerator('Ctrl+ArrowUp')).toBe('CommandOrControl+Up');
  });

  it('maps Escape to Esc', () => {
    expect(toAccelerator('Ctrl+Escape')).toBe('CommandOrControl+Esc');
  });

  it('maps space to Space', () => {
    expect(toAccelerator('Ctrl+ ')).toBe('CommandOrControl+Space');
  });

  it('preserves function keys', () => {
    expect(toAccelerator('Ctrl+F5')).toBe('CommandOrControl+F5');
  });
});
