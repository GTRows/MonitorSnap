import { useEffect, useState, Component, type ErrorInfo, type ReactNode } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Sidebar } from '@/components/Sidebar';
import { PresetsPage } from '@/pages/PresetsPage';
import { DisplaysPage } from '@/pages/DisplaysPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { AboutPage } from '@/pages/AboutPage';
import { useAppStore } from '@/stores/appStore';
import { usePresetStore } from '@/stores/presetStore';
import { useSettingsStore } from '@/stores/settingsStore';
import { ToastContainer } from '@/components/ToastContainer';
import { BackendErrorScreen } from '@/components/BackendErrorScreen';

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
    if (!backendStatus.ready) return;
    fetchPresets();
    fetchCurrentDisplays();
    fetchSettings();
  }, [backendStatus.ready, fetchPresets, fetchCurrentDisplays, fetchSettings]);

  // Apply theme class
  useEffect(() => {
    document.documentElement.classList.toggle('dark', resolvedTheme === 'dark');
  }, [resolvedTheme]);

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
