import { create } from 'zustand';
import type { HotkeyStatus, HotkeyStatusMap } from '@/types';

interface HotkeyStatusState {
  statuses: HotkeyStatusMap;
  setStatuses: (statuses: HotkeyStatusMap) => void;
  statusFor: (presetId: string) => HotkeyStatus | null;
}

export const useHotkeyStatusStore = create<HotkeyStatusState>((set, get) => ({
  statuses: {},
  setStatuses: (statuses) => set({ statuses }),
  statusFor: (presetId) => get().statuses[presetId] ?? null,
}));
