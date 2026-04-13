import { useState, useCallback, useRef } from 'react';
import { X, Keyboard, AlertTriangle } from 'lucide-react';
import { formatKeyCombo } from '@/lib/hotkey';

interface HotkeyInputProps {
  value: string | null;
  onChange: (hotkey: string | null) => void;
  existingHotkeys?: string[];
  className?: string;
}

export function HotkeyInput({ value, onChange, existingHotkeys = [], className = '' }: HotkeyInputProps) {
  const [listening, setListening] = useState(false);
  const inputRef = useRef<HTMLDivElement>(null);

  const hasConflict = value != null && existingHotkeys.includes(value);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      e.preventDefault();
      e.stopPropagation();

      if (e.key === 'Escape') {
        setListening(false);
        return;
      }

      const combo = formatKeyCombo(e.nativeEvent);
      if (combo) {
        onChange(combo);
        setListening(false);
      }
    },
    [onChange]
  );

  const startListening = () => {
    setListening(true);
    inputRef.current?.focus();
  };

  const clear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange(null);
    setListening(false);
  };

  return (
    <div className={`flex flex-col gap-1 ${className}`}>
      <div
        ref={inputRef}
        tabIndex={0}
        onClick={startListening}
        onKeyDown={listening ? handleKeyDown : undefined}
        onBlur={() => setListening(false)}
        className={`
          group flex items-center gap-2 h-8 px-3 rounded-fluent border cursor-pointer
          transition-all duration-150 outline-none
          ${listening
            ? 'border-accent bg-accent/5 shadow-fluent-focus'
            : hasConflict
              ? 'border-yellow-500/70 bg-yellow-500/5'
              : 'border-border-default bg-[var(--input-bg)] hover:border-border-default/80'
          }
        `}
      >
        <Keyboard size={14} className="text-text-tertiary shrink-0" />
        <span className={`text-body flex-1 ${value ? 'text-text-primary' : 'text-text-tertiary'}`}>
          {listening ? 'Press a key combination...' : value ?? 'None'}
        </span>
        {hasConflict && !listening && (
          <AlertTriangle size={13} className="text-yellow-500 shrink-0" />
        )}
        {value && !listening && (
          <button
            onClick={clear}
            className="opacity-0 group-hover:opacity-100 transition-opacity duration-150 text-text-tertiary hover:text-text-primary cursor-pointer"
          >
            <X size={14} />
          </button>
        )}
      </div>
      {hasConflict && (
        <p className="text-[11px] text-yellow-500 px-1">
          Already used by another preset
        </p>
      )}
    </div>
  );
}
