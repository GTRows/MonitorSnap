import { motion } from 'framer-motion';

interface ToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export function Toggle({ checked, onChange, disabled = false }: ToggleProps) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`
        relative w-10 h-5 rounded-full transition-colors duration-200 cursor-pointer
        focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent
        ${checked ? 'bg-accent' : 'bg-[var(--toggle-off-bg)]'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      <motion.div
        animate={{ x: checked ? 20 : 2 }}
        transition={{ type: 'spring', stiffness: 500, damping: 30 }}
        className="absolute top-[2px] w-4 h-4 rounded-full bg-white shadow-sm"
      />
    </button>
  );
}
