import { useEffect, useState, Component, type ErrorInfo, type ReactNode } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Sidebar } from '@/components/Sidebar';
import { PresetsPage } from '@/pages/PresetsPage';
import { DisplaysPage } from '@/pages/DisplaysPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { AboutPage } from '@/pages/AboutPage';
import { useAppStore } from '@/stores/appStore';
import { notifyPresetApplied, usePresetStore } from '@/stores/presetStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { ToastContainer } from '@/components/ToastContainer';
import { BackendErrorScreen } from '@/components/BackendErrorScreen';
import { UpdateBanner } from '@/components/UpdateBanner';
import { useUpdateStore } from '@/stores/updateStore';
import { useHotkeyStatusStore } from '@/stores/hotkeyStatusStore';

class PageErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[PageError]', error, info.componentStack);
  }
  render() {
    if (this.state.error) {
      return (
        <div className="flex-1 flex flex-col items-center justify-center p-8 gap-3">
          <p className="text-body font-medium text-red-400">Page failed to render</p>
          <p className="text-caption text-text-tertiary font-mono max-w-[600px] break-words text-center">
            {this.state.error.message}
          </p>
          <button
            onClick={() => this.setState({ error: null })}
            className="mt-2 px-3 py-1.5 rounded-fluent text-body bg-accent text-[#000] cursor-pointer"
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const pages = {
  presets: PresetsPage,
  displays: DisplaysPage,
  settings: SettingsPage,
  about: AboutPage,
};

export function App() {
  const { currentPage } = useAppStore();
  const fetchPresets = usePresetStore((s) => s.fetchPresets);
  const fetchCurrentDisplays = usePresetStore((s) => s.fetchCurrentDisplays);
  const fetchSettings = useSettingsStore((s) => s.fetchSettings);
  const resolvedTheme = useSettingsStore((s) => s.resolvedTheme);
  const setResolvedTheme = useSettingsStore((s) => s.setResolvedTheme);
  const [backendStatus, setBackendStatus] = useState<{ ready: boolean; error: string | null }>({
    ready: true,
    error: null,
  });

  useEffect(() => {
    if (!window.api) return;
    window.api.getBackendStatus().then(setBackendStatus);
    const unsubscribe = window.api.onBackendStatusChanged(setBackendStatus);
    return unsubscribe;
  }, []);

  useEffect(() => {
    if (!window.api) return;
    const setInfo = useUpdateStore.getState().setInfo;
    window.api.getLastUpdateInfo().then((cached) => {
      if (cached) setInfo(cached);
    });
    const unsubscribe = window.api.onUpdateAvailable((info) => {
      setInfo(info);
    });
    return unsubscribe;
  }, []);

  useEffect(() => {
    if (!window.api) return;
    const setStatuses = useHotkeyStatusStore.getState().setStatuses;
    window.api.getHotkeyStatuses().then(setStatuses);
    const unsubscribe = window.api.onHotkeyStatusesChanged(setStatuses);
    return unsubscribe;
  }, []);

  // Tray-triggered actions. Listen globally so they work from any page.
  useEffect(() => {
    if (!window.api) return;
    const { setPage, setPendingAction } = useAppStore.getState();
    const applyPreset = usePresetStore.getState().applyPreset;
    const fetchCurrentDisplays = usePresetStore.getState().fetchCurrentDisplays;
    const unsubApply = window.api.onApplyPreset((presetId) => {
      applyPreset(presetId);
    });
    const unsubSave = window.api.onSaveCurrentConfig(() => {
      setPage('presets');
      setPendingAction('new-preset');
    });
    const unsubApplied = window.api.onPresetApplied((presetId) => {
      fetchCurrentDisplays();
      const preset = usePresetStore.getState().presets.find((p) => p.id === presetId);
      notifyPresetApplied(preset?.name ?? presetId);
    });
    return () => { unsubApply(); unsubSave(); unsubApplied(); };
  }, []);

  useEffect(() => {
    if (!backendStatus.ready) return;
    fetchPresets();
    fetchCurrentDisplays();
    fetchSettings();
  }, [backendStatus.ready, fetchPresets, fetchCurrentDisplays, fetchSettings]);

  // Apply theme class
  useEffect(() => {
    document.documentElement.classList.toggle('dark', resolvedTheme === 'dark');
  }, [resolvedTheme]);

  // Apply font scale to the root element so rem-based typography scales.
  const fontScale = useSettingsStore((s) => s.settings.fontScale);
  useEffect(() => {
    const safe = Number.isFinite(fontScale) && fontScale > 0 ? fontScale : 1;
    document.documentElement.style.fontSize = `${16 * safe}px`;
    return () => { document.documentElement.style.fontSize = ''; };
  }, [fontScale]);

  // Escape-to-minimize: pressing Escape outside any input or modal hides the
  // window when the setting is on. Inputs/textareas and contenteditable get
  // their own Escape handling (cancel rename, close context menu, etc.) so we
  // skip those cases.
  const escToMinimize = useSettingsStore((s) => s.settings.escToMinimize);
  useEffect(() => {
    if (!escToMinimize || !window.api) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key !== 'Escape' || e.defaultPrevented) return;
      const target = e.target as HTMLElement | null;
      if (!target) return;
      const tag = target.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || target.isContentEditable) return;
      window.api.hideWindow();
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [escToMinimize]);

  // Listen for system theme changes
  useEffect(() => {
    if (!window.api) {
      const mq = window.matchMedia('(prefers-color-scheme: dark)');
      const handler = (e: MediaQueryListEvent) => setResolvedTheme(e.matches ? 'dark' : 'light');
      mq.addEventListener('change', handler);
      return () => mq.removeEventListener('change', handler);
    }

    const unsubscribe = window.api.onThemeChanged((theme) => {
      setResolvedTheme(theme);
    });
    return unsubscribe;
  }, [setResolvedTheme]);

  const PageComponent = pages[currentPage];

  return (
    <div className="flex h-screen bg-surface-base text-text-primary select-none overflow-hidden">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Drag region for frameless window */}
        <div className="h-[40px] shrink-0 app-drag-region" />
        <UpdateBanner />
        <div className="flex-1 relative overflow-hidden">
          <AnimatePresence mode="sync">
            <motion.div
              key={currentPage}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.12 }}
              className="absolute inset-0 flex overflow-hidden"
            >
              <PageErrorBoundary>
                <PageComponent />
              </PageErrorBoundary>
            </motion.div>
          </AnimatePresence>
        </div>
      </main>
      <ToastContainer />
      {!backendStatus.ready && (
        <BackendErrorScreen
          error={backendStatus.error ?? 'Backend is starting...'}
          onRetry={() => window.api.restartBackend()}
        />
      )}
    </div>
  );
}
