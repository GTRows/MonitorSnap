import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { motion, AnimatePresence } from 'framer-motion';

interface TooltipProps {
  content: string;
}

export function Tooltip({ content }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });
  const triggerRef = useRef<HTMLButtonElement>(null);
  const tooltipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!visible || !triggerRef.current) return;

    const rect = triggerRef.current.getBoundingClientRect();
    const tooltipWidth = 220;
    const gap = 8;

    let left = rect.left + rect.width / 2 - tooltipWidth / 2;
    // Keep inside viewport
    left = Math.max(8, Math.min(left, window.innerWidth - tooltipWidth - 8));

    setCoords({
      top: rect.bottom + gap,
      left,
    });
  }, [visible]);

  return (
    <>
      <button
        ref={triggerRef}
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
        className="inline-flex items-center justify-center w-4 h-4 rounded-full border border-border-default text-text-tertiary hover:border-accent hover:text-accent transition-colors duration-150 cursor-default shrink-0"
        tabIndex={0}
        aria-label="More information"
      >
        <span className="text-[9px] font-bold leading-none select-none">?</span>
      </button>

      {createPortal(
        <AnimatePresence>
          {visible && (
            <motion.div
              ref={tooltipRef}
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.12 }}
              className="fixed z-[500] w-[220px] px-3 py-2.5 rounded-fluent border border-border-subtle bg-surface-overlay shadow-fluent-lg text-caption text-text-secondary leading-relaxed pointer-events-none"
              style={{ top: coords.top, left: coords.left }}
            >
              {content}
            </motion.div>
          )}
        </AnimatePresence>,
        document.body
      )}
    </>
  );
}
