import { motion } from 'framer-motion';
import { Monitor, FolderOpen, AlertTriangle, Bug, Github, ExternalLink } from 'lucide-react';
import { openLink } from '@/lib/openLink';
import { GITHUB_NEW_ISSUE, GITHUB_REPO, GITHUB_ISSUES, APP_VERSION } from '@/lib/constants';

function LinkButton({
  label,
  icon: Icon,
  href,
  variant = 'default',
}: {
  label: string;
  icon: typeof Bug;
  href: string;
  variant?: 'default' | 'primary';
}) {
  return (
    <button
      onClick={() => openLink(href)}
      className={`
        flex items-center gap-2 px-3 py-2 rounded-fluent text-body cursor-pointer
        transition-colors duration-150 border
        ${variant === 'primary'
          ? 'border-accent bg-accent/10 text-accent hover:bg-accent/15'
          : 'border-border-subtle text-text-secondary hover:border-border-default hover:text-text-primary'
        }
      `}
    >
      <Icon size={15} />
      {label}
      <ExternalLink size={12} className="ml-auto opacity-50" />
    </button>
  );
}

export function AboutPage() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className="flex-1 p-5 overflow-y-auto"
    >
      <div className="max-w-[540px]">
        {/* App identity */}
        <div className="flex items-center gap-4 mb-6">
          <div className="w-14 h-14 rounded-fluent-lg bg-accent/10 flex items-center justify-center">
            <Monitor size={28} className="text-accent" />
          </div>
          <div>
            <h2 className="text-title font-semibold text-text-primary">DisplayPresets</h2>
            <p className="text-caption text-text-tertiary">Version {APP_VERSION}</p>
          </div>
        </div>

        {/* Description */}
        <div className="rounded-fluent-lg border border-border-subtle p-4 mb-4">
          <p className="text-body text-text-secondary leading-relaxed">
            Save and restore monitor configurations instantly. Designed for KVM switch users,
            multi-monitor setups, and anyone who frequently changes display arrangements.
          </p>
          <p className="text-body text-text-secondary leading-relaxed mt-2">
            Captures monitor positions, resolutions, refresh rates, orientations, scale factors,
            and primary display assignment. Apply saved configurations with a single click or
            global hotkey.
          </p>
        </div>

        {/* Links */}
        <div className="rounded-fluent-lg border border-border-subtle p-4 mb-4">
          <div className="flex items-center gap-2 mb-3">
            <Github size={16} className="text-text-tertiary" />
            <h3 className="text-body font-medium text-text-primary">GitHub</h3>
          </div>
          <div className="flex flex-col gap-2">
            <LinkButton
              label="Repository"
              icon={Github}
              href={GITHUB_REPO}
              variant="primary"
            />
            <LinkButton
              label="Report a bug"
              icon={Bug}
              href={`${GITHUB_NEW_ISSUE}?template=bug_report.md`}
            />
            <LinkButton
              label="Issues"
              icon={ExternalLink}
              href={GITHUB_ISSUES}
            />
          </div>
        </div>

        {/* Data storage */}
        <div className="rounded-fluent-lg border border-border-subtle p-4 mb-4">
          <div className="flex items-center gap-2 mb-2">
            <FolderOpen size={16} className="text-text-tertiary" />
            <h3 className="text-body font-medium text-text-primary">Data Storage</h3>
          </div>
          <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-caption">
            <span className="text-text-tertiary">Presets</span>
            <code className="text-text-secondary font-mono">%APPDATA%\DisplayPresets\presets\</code>
            <span className="text-text-tertiary">Settings</span>
            <code className="text-text-secondary font-mono">%APPDATA%\DisplayPresets\settings.json</code>
          </div>
        </div>

        {/* Limitations */}
        <div className="rounded-fluent-lg border border-border-subtle p-4 mb-4">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={16} className="text-text-tertiary" />
            <h3 className="text-body font-medium text-text-primary">Limitations</h3>
          </div>
          <ul className="text-caption text-text-secondary space-y-1.5 ml-0.5">
            <li className="flex gap-2">
              <span className="text-text-tertiary shrink-0">--</span>
              Windows 11 only. Uses Windows Display Configuration API.
            </li>
            <li className="flex gap-2">
              <span className="text-text-tertiary shrink-0">--</span>
              Monitors must be physically connected for presets to apply correctly.
            </li>
            <li className="flex gap-2">
              <span className="text-text-tertiary shrink-0">--</span>
              Some configurations may require administrator privileges.
            </li>
            <li className="flex gap-2">
              <span className="text-text-tertiary shrink-0">--</span>
              HDR and color profile settings are not captured.
            </li>
          </ul>
        </div>

      </div>
    </motion.div>
  );
}
