import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface ContextMenuItem {
  label: string;
  icon?: React.ReactNode;
  onClick: () => void;
  danger?: boolean;
  separator?: boolean;
}

interface ContextMenuProps {
  x: number;
  y: number;
  items: ContextMenuItem[];
  onClose: () => void;
}

export function ContextMenu({ x, y, items, onClose }: ContextMenuProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const keyHandler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('mousedown', handler);
    document.addEventListener('keydown', keyHandler);
    return () => {
      document.removeEventListener('mousedown', handler);
      document.removeEventListener('keydown', keyHandler);
    };
  }, [onClose]);

  return (
    <AnimatePresence>
      <motion.div
        ref={ref}
        initial={{ opacity: 0, scale: 0.95, y: -4 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: -4 }}
        transition={{ duration: 0.12 }}
        className="fixed z-[100] min-w-[180px] py-1.5 rounded-fluent-lg border border-border-subtle bg-surface-overlay shadow-fluent-lg backdrop-blur-xl"
        style={{ left: x, top: y }}
      >
        {items.map((item, i) =>
          item.separator ? (
            <div key={i} className="my-1.5 mx-3 h-px bg-border-subtle" />
          ) : (
            <button
              key={i}
              onClick={() => {
                item.onClick();
                onClose();
              }}
              className={`
                w-full flex items-center gap-2.5 px-3 py-1.5 text-body cursor-pointer
                transition-colors duration-100
                ${item.danger
                  ? 'text-red-400 hover:bg-red-500/10'
                  : 'text-text-primary hover:bg-[var(--nav-hover-bg)]'
                }
              `}
            >
              {item.icon && <span className="w-4 h-4 flex items-center justify-center">{item.icon}</span>}
              {item.label}
            </button>
          )
        )}
      </motion.div>
    </AnimatePresence>
  );
}
