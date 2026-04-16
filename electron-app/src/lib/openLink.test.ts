// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { openLink } from './openLink';

describe('openLink', () => {
  let originalApi: unknown;
  let originalWindowOpen: typeof window.open;

  beforeEach(() => {
    originalApi = (window as unknown as { api?: unknown }).api;
    originalWindowOpen = window.open;
    (window as unknown as { api?: unknown }).api = undefined;
    window.open = vi.fn();
  });

  afterEach(() => {
    (window as unknown as { api?: unknown }).api = originalApi;
    window.open = originalWindowOpen;
  });

  it('delegates to window.api.openExternal when available', () => {
    const openExternal = vi.fn();
    (window as unknown as { api: { openExternal: typeof openExternal } }).api = { openExternal };

    openLink('https://example.com');

    expect(openExternal).toHaveBeenCalledWith('https://example.com');
    expect(window.open).not.toHaveBeenCalled();
  });

  it('falls back to window.open when api is missing', () => {
    openLink('https://example.com');

    expect(window.open).toHaveBeenCalledWith(
      'https://example.com',
      '_blank',
      'noopener,noreferrer',
    );
  });

  it('falls back to window.open when api exists but openExternal is missing', () => {
    (window as unknown as { api: Record<string, unknown> }).api = {};

    openLink('https://example.com');

    expect(window.open).toHaveBeenCalled();
  });
});
