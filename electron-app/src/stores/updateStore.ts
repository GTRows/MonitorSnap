import { create } from 'zustand';
import type { UpdateInfo } from '@/types';

interface UpdateState {
  info: UpdateInfo | null;
  checking: boolean;
  dismissedVersion: string | null;
  setInfo: (info: UpdateInfo | null) => void;
  check: () => Promise<void>;
  dismiss: () => void;
}

export const useUpdateStore = create<UpdateState>((set, get) => ({
  info: null,
  checking: false,
  dismissedVersion: null,

  setInfo: (info) => set({ info }),

  check: async () => {
    if (!window.api) return;
    set({ checking: true });
    try {
      const info = await window.api.checkForUpdates();
      set({ info, checking: false });
    } catch (err) {
      set({
        info: {
          available: false,
          currentVersion: get().info?.currentVersion ?? '',
          latestVersion: null,
          releaseUrl: null,
          releaseNotes: null,
          publishedAt: null,
          checkedAt: new Date().toISOString(),
          error: err instanceof Error ? err.message : String(err),
        },
        checking: false,
      });
    }
  },

  dismiss: () => {
    const latest = get().info?.latestVersion ?? null;
    set({ dismissedVersion: latest });
  },
}));
