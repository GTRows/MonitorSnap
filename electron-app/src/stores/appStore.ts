import { create } from 'zustand';
import type { Page } from '@/types';

interface AppState {
  currentPage: Page;
  setPage: (page: Page) => void;
}

export const useAppStore = create<AppState>((set) => ({
  currentPage: 'presets',
  setPage: (page) => set({ currentPage: page }),
}));
