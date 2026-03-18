"""
MonitorSnap - Display Configuration Manager

Usage:
    python -m display_presets <command>    Run CLI command
    python -m display_presets.server      Start HTTP backend (used by Electron)

CLI Commands:
    list                    List all saved presets
    apply <name>            Apply a preset
    save <name>             Save current display config
    delete <name>           Delete a preset
    rename <old> <new>      Rename a preset
    current                 Show current display config
    info <name>             Show preset details
    --help                  Show help
    --version               Show version
"""

import sys


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print(__doc__.strip())
        sys.exit(0)

    try:
        from display_presets.cli import run_cli
        sys.exit(run_cli())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
