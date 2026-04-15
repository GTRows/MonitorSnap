import { useState } from 'react';
import { motion } from 'framer-motion';

interface BackendErrorScreenProps {
  error: string;
  onRetry: () => Promise<{ success: boolean; error?: string }>;
}

export function BackendErrorScreen({ error, onRetry }: BackendErrorScreenProps) {
  const [retrying, setRetrying] = useState(false);

  const handleRetry = async () => {
    setRetrying(true);
    try {
      await onRetry();
    } finally {
      setRetrying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center bg-surface-base">
      <div className="h-[40px] absolute top-0 left-0 right-0 app-drag-region" />
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.18 }}
        className="w-[520px] max-w-[92vw] p-7 rounded-fluent-lg bg-surface-overlay border border-border-subtle shadow-fluent-lg"
      >
        <div className="flex items-start gap-4">
          <div className="shrink-0 w-10 h-10 rounded-full bg-red-500/15 border border-red-500/30 flex items-center justify-center">
            <span className="text-red-400 text-lg font-semibold leading-none">!</span>
          </div>
          <div className="flex-1 min-w-0">
            <h2 className="text-subtitle font-semibold text-text-primary">
              Backend failed to start
            </h2>
            <p className="mt-1 text-body text-text-secondary">
              MonitorSnap couldn't reach its Python backend. Display presets and
              configuration changes are unavailable until it starts.
            </p>
          </div>
        </div>

        <div className="mt-5 p-3 rounded-fluent bg-black/25 border border-border-subtle max-h-[180px] overflow-auto">
          <pre className="text-caption font-mono text-text-tertiary whitespace-pre-wrap break-words">
            {error || 'Unknown error'}
          </pre>
        </div>

        <div className="mt-5 text-caption text-text-tertiary leading-relaxed">
          <p className="font-medium text-text-secondary mb-1">Common causes</p>
          <ul className="list-disc ml-5 space-y-0.5">
            <li>Python 3.10+ is not installed or not on PATH</li>
            <li>An antivirus blocked the bundled backend</li>
            <li>A previous instance is still holding a port</li>
          </ul>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="px-4 py-1.5 text-body rounded-fluent font-medium bg-accent text-[#000] hover:bg-accent-hover disabled:opacity-60 disabled:cursor-not-allowed transition-colors duration-150 cursor-pointer"
          >
            {retrying ? 'Retrying...' : 'Retry'}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
