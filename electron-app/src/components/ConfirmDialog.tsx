import { motion, AnimatePresence } from 'framer-motion';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = 'Confirm',
  danger = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[200] bg-black/40"
            onClick={onCancel}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 8 }}
            transition={{ duration: 0.15 }}
            className="fixed z-[201] top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[360px] p-6 rounded-fluent-lg bg-surface-overlay border border-border-subtle shadow-fluent-lg"
          >
            <h3 className="text-subtitle font-semibold text-text-primary">{title}</h3>
            <p className="mt-2 text-body text-text-secondary">{message}</p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                onClick={onCancel}
                className="px-4 py-1.5 text-body rounded-fluent border border-border-default text-text-primary hover:bg-[var(--nav-hover-bg)] transition-colors duration-150 cursor-pointer"
              >
                Cancel
              </button>
              <button
                onClick={onConfirm}
                className={`
                  px-4 py-1.5 text-body rounded-fluent font-medium transition-colors duration-150 cursor-pointer
                  ${danger
                    ? 'bg-red-500 text-white hover:bg-red-600'
                    : 'bg-accent text-[#000] hover:bg-accent-hover'
                  }
                `}
              >
                {confirmLabel}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
