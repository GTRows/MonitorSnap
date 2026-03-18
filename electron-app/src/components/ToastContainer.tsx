import { AnimatePresence, motion } from 'framer-motion';
import { X, CheckCircle, AlertCircle, Info } from 'lucide-react';
import { useToastStore } from '@/stores/toastStore';

const icons = {
  success: CheckCircle,
  error: AlertCircle,
  info: Info,
};

const colors = {
  success: 'text-green-400',
  error: 'text-red-400',
  info: 'text-accent',
};

export function ToastContainer() {
  const { toasts, dismiss } = useToastStore();

  return (
    <div className="fixed bottom-5 right-5 z-[1000] flex flex-col gap-2 pointer-events-none">
      <AnimatePresence mode="sync">
        {toasts.map((toast) => {
          const Icon = icons[toast.type];
          return (
            <motion.div
              key={toast.id}
              initial={{ opacity: 0, y: 12, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 6, scale: 0.96 }}
              transition={{ duration: 0.18 }}
              className="pointer-events-auto flex items-center gap-3 pl-3 pr-2 py-2.5 rounded-fluent-lg border border-border-subtle bg-surface-overlay shadow-fluent-lg min-w-[260px] max-w-[340px]"
            >
              <Icon size={16} className={`shrink-0 ${colors[toast.type]}`} />
              <span className="flex-1 text-body text-text-primary">{toast.message}</span>
              <button
                onClick={() => dismiss(toast.id)}
                className="shrink-0 p-1 rounded text-text-tertiary hover:text-text-primary transition-colors cursor-pointer"
              >
                <X size={13} />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
