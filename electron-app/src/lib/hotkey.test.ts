import { describe, it, expect } from 'vitest';
import { formatKeyCombo } from './hotkey';

function evt(overrides: Partial<{ key: string; ctrlKey: boolean; altKey: boolean; shiftKey: boolean; metaKey: boolean }>) {
  return {
    key: 'a',
    ctrlKey: false,
    altKey: false,
    shiftKey: false,
    metaKey: false,
    ...overrides,
  };
}

describe('formatKeyCombo', () => {
  it('captures a simple Ctrl+letter combo', () => {
    expect(formatKeyCombo(evt({ key: 'a', ctrlKey: true }))).toBe('Ctrl+A');
  });

  it('preserves modifier order Ctrl, Alt, Shift, Win', () => {
    expect(
      formatKeyCombo(evt({ key: 's', ctrlKey: true, altKey: true, shiftKey: true, metaKey: true }))
    ).toBe('Ctrl+Alt+Shift+Win+S');
  });

  it('normalizes shifted glyphs to their base key', () => {
    expect(formatKeyCombo(evt({ key: '*', ctrlKey: true, altKey: true, shiftKey: true })))
      .toBe('Ctrl+Alt+Shift+8');
    expect(formatKeyCombo(evt({ key: '?', ctrlKey: true, shiftKey: true })))
      .toBe('Ctrl+Shift+/');
  });

  it('leaves non-shifted punctuation alone', () => {
    expect(formatKeyCombo(evt({ key: '-', ctrlKey: true, altKey: true, shiftKey: true })))
      .toBe('Ctrl+Alt+Shift+-');
  });

  it('rejects modifier-only presses', () => {
    expect(formatKeyCombo(evt({ key: 'Control', ctrlKey: true }))).toBeNull();
    expect(formatKeyCombo(evt({ key: 'Shift', shiftKey: true }))).toBeNull();
  });

  it('rejects combos with no modifier', () => {
    expect(formatKeyCombo(evt({ key: 'a' }))).toBeNull();
  });

  it('preserves multi-character keys like F5 as-is', () => {
    expect(formatKeyCombo(evt({ key: 'F5', ctrlKey: true }))).toBe('Ctrl+F5');
  });

  it('uppercases single-character non-shifted keys', () => {
    expect(formatKeyCombo(evt({ key: 'b', altKey: true }))).toBe('Alt+B');
  });

  it('preserves digits', () => {
    expect(formatKeyCombo(evt({ key: '1', ctrlKey: true }))).toBe('Ctrl+1');
  });
});
