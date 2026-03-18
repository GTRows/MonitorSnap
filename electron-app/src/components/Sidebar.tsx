import { motion } from 'framer-motion';
import { Monitor, LayoutGrid, Settings, Info, Bug } from 'lucide-react';
import { useAppStore } from '@/stores/appStore';
import { openLink } from '@/lib/openLink';
import { GITHUB_REPO, APP_VERSION } from '@/lib/constants';
import type { Page } from '@/types';

const navItems: Array<{ id: Page; label: string; icon: typeof Monitor }> = [
  { id: 'presets', label: 'Presets', icon: LayoutGrid },
  { id: 'displays', label: 'Displays', icon: Monitor },
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'about', label: 'About', icon: Info },
];

export function Sidebar() {
  const { currentPage, setPage } = useAppStore();

  return (
    <nav className="w-[220px] shrink-0 flex flex-col bg-surface-base border-r border-border-subtle pt-[40px]">
      <div className="px-5 py-4 flex items-center gap-2.5">
        <img src="./icon.png" alt="" className="w-6 h-6 shrink-0" draggable={false} />
        <h1 className="text-subtitle font-semibold text-text-primary tracking-tight">
          DisplayPresets
        </h1>
      </div>

      <div className="flex flex-col gap-0.5 px-3 mt-1">
        {navItems.map((item) => {
          const isActive = currentPage === item.id;
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              className={`
                relative flex items-center gap-3 px-3 py-2 rounded-fluent
                text-body font-normal cursor-pointer
                transition-colors duration-150
                ${isActive
                  ? 'text-text-primary bg-[var(--nav-active-bg)]'
                  : 'text-text-secondary hover:text-text-primary hover:bg-[var(--nav-hover-bg)]'
                }
              `}
            >
              {isActive && (
                <motion.div
                  layoutId="nav-indicator"
                  className="absolute left-0 top-[8px] bottom-[8px] w-[3px] rounded-full bg-accent"
                  transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                />
              )}
              <Icon size={18} strokeWidth={isActive ? 2 : 1.5} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="mt-auto px-3 pb-4 flex flex-col gap-1">
        <button
          onClick={() => openLink(GITHUB_REPO)}
          className="flex items-center gap-2 px-3 py-1.5 rounded-fluent text-caption text-text-tertiary hover:text-text-secondary hover:bg-[var(--nav-hover-bg)] transition-colors duration-150 cursor-pointer w-full"
        >
          <Bug size={13} strokeWidth={1.5} />
          Contribute / Report bug
        </button>
        <p className="text-caption text-text-tertiary px-3">v{APP_VERSION}</p>
      </div>
    </nav>
  );
}
