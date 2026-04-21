import { motion } from 'framer-motion';
import {
  Monitor,
  FolderOpen,
  AlertTriangle,
  Bug,
  Github,
  ExternalLink,
  Download,
  RefreshCw,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';
import { openLink } from '@/lib/openLink';
import { GITHUB_NEW_ISSUE, GITHUB_REPO, GITHUB_ISSUES, APP_VERSION } from '@/lib/constants';
import { useUpdateStore } from '@/stores/updateStore';

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

function formatCheckedAt(iso: string): string {
  try {
    const d = new Date(iso);
    const now = Date.now();
    const diff = now - d.getTime();
    if (diff < 60_000) return 'just now';
    if (diff < 3_600_000) return `${Math.floor(diff / 60_000)} min ago`;
    if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)} h ago`;
    return d.toLocaleDateString();
  } catch {
    return iso;
  }
}

function UpdateCard() {
  const info = useUpdateStore((s) => s.info);
  const checking = useUpdateStore((s) => s.checking);
  const check = useUpdateStore((s) => s.check);

  const hasUpdate = !!info?.available && !!info.latestVersion;
  const hasError = !!info?.error;

  return (
    <div className="rounded-fluent-lg border border-border-subtle p-4 mb-4">
      <div className="flex items-center gap-2 mb-3">
        {hasUpdate ? (
          <Sparkles size={16} className="text-accent" />
        ) : (
          <CheckCircle2 size={16} className="text-text-tertiary" />
        )}
        <h3 className="text-body font-medium text-text-primary">Updates</h3>
      </div>

      <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1.5 text-caption mb-3">
        <span className="text-text-tertiary">Installed</span>
        <code className="text-text-secondary font-mono">v{APP_VERSION}</code>
        <span className="text-text-tertiary">Latest</span>
        <code
          className={`font-mono ${
            hasUpdate ? 'text-accent font-semibold' : 'text-text-secondary'
          }`}
        >
          {info?.latestVersion ? `v${info.latestVersion}` : '--'}
        </code>
        <span className="text-text-tertiary">Last checked</span>
        <span className="text-text-secondary">
          {info ? formatCheckedAt(info.checkedAt) : 'Not checked yet'}
        </span>
      </div>

      {hasError && (
        <p className="text-caption text-red-400 mb-3 break-words">
          Check failed: {info?.error}
        </p>
      )}

      {!hasUpdate && !hasError && info && (
        <p className="text-caption text-text-tertiary mb-3">
          You are running the latest version.
        </p>
      )}

      <div className="flex items-center gap-2">
        {hasUpdate && info?.releaseUrl && (
          <button
            onClick={() => openLink(info.releaseUrl!)}
            className="
              flex items-center gap-1.5 px-3 py-1.5 rounded-fluent
              text-caption font-medium
              bg-accent text-black hover:bg-accent-hover
              transition-colors duration-150 cursor-pointer
            "
          >
            <Download size={13} />
            Download v{info.latestVersion}
          </button>
        )}
        <button
          onClick={check}
          disabled={checking}
          className="
            flex items-center gap-1.5 px-3 py-1.5 rounded-fluent
            text-caption
            border border-border-subtle text-text-secondary
            hover:border-border-default hover:text-text-primary
            disabled:opacity-60 disabled:cursor-not-allowed
            transition-colors duration-150 cursor-pointer
          "
        >
          <RefreshCw size={13} className={checking ? 'animate-spin' : ''} />
          {checking ? 'Checking...' : 'Check for updates'}
        </button>
      </div>
    </div>
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
            <h2 className="text-title font-semibold text-text-primary">MonitorSnap</h2>
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

        <UpdateCard />

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
            <code className="text-text-secondary font-mono">%APPDATA%\MonitorSnap\presets\</code>
            <span className="text-text-tertiary">Settings</span>
            <code className="text-text-secondary font-mono">%APPDATA%\MonitorSnap\settings.json</code>
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
