import { AnimatePresence, motion } from 'framer-motion';
import { Download, Sparkles, X } from 'lucide-react';
import { useUpdateStore } from '@/stores/updateStore';
import { openLink } from '@/lib/openLink';

export function UpdateBanner() {
  const info = useUpdateStore((s) => s.info);
  const dismissedVersion = useUpdateStore((s) => s.dismissedVersion);
  const dismiss = useUpdateStore((s) => s.dismiss);

  const shouldShow =
    !!info &&
    info.available &&
    !!info.latestVersion &&
    info.latestVersion !== dismissedVersion;

  return (
    <AnimatePresence>
      {shouldShow && info && (
        <motion.div
          initial={{ opacity: 0, y: -12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
          className="shrink-0 px-5 pt-2"
        >
          <div
            className="
              relative overflow-hidden
              rounded-fluent-lg border border-accent/30
              bg-gradient-to-r from-accent/10 via-accent/5 to-transparent
              shadow-fluent
            "
          >
            {/* Soft glow accent bar */}
            <div className="absolute inset-y-0 left-0 w-[3px] bg-accent" />

            <div className="flex items-center gap-3 pl-4 pr-2 py-2.5">
              <div className="w-8 h-8 rounded-fluent bg-accent/15 flex items-center justify-center shrink-0">
                <Sparkles size={16} className="text-accent" />
              </div>

              <div className="flex-1 min-w-0">
                <p className="text-body text-text-primary leading-tight">
                  <span className="font-medium">New version available</span>
                  <span className="text-text-tertiary font-normal ml-2">
                    v{info.currentVersion} <span className="opacity-60">-&gt;</span>{' '}
                    <span className="text-accent font-mono">v{info.latestVersion}</span>
                  </span>
                </p>
              </div>

              <button
                onClick={() => info.releaseUrl && openLink(info.releaseUrl)}
                className="
                  flex items-center gap-1.5 px-3 py-1.5 rounded-fluent
                  text-caption font-medium
                  bg-accent text-black hover:bg-accent-hover
                  transition-colors duration-150 cursor-pointer
                "
              >
                <Download size={13} />
                Download
              </button>

              <button
                onClick={dismiss}
                aria-label="Dismiss update notification"
                className="
                  w-7 h-7 rounded-fluent flex items-center justify-center
                  text-text-tertiary hover:text-text-primary
                  hover:bg-surface-overlay
                  transition-colors duration-150 cursor-pointer
                "
              >
                <X size={14} />
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
