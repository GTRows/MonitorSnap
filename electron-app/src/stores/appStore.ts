import { create } from 'zustand';
import type { Page } from '@/types';

// Actions queued from outside the React tree (e.g. tray menu clicks) that the
// target page consumes on mount or when it becomes active.
export type PendingAction = 'new-preset' | null;

interface AppState {
  currentPage: Page;
  pendingAction: PendingAction;
  setPage: (page: Page) => void;
  setPendingAction: (action: PendingAction) => void;
  consumePendingAction: () => PendingAction;
}

export const useAppStore = create<AppState>((set, get) => ({
  currentPage: 'presets',
  pendingAction: null,
  setPage: (page) => set({ currentPage: page }),
  setPendingAction: (action) => set({ pendingAction: action }),
  consumePendingAction: () => {
    const action = get().pendingAction;
    if (action) set({ pendingAction: null });
    return action;
  },
}));
