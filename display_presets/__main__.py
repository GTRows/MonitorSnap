"""
MonitorSnap - Display Configuration Manager

Usage:
    python -m display_presets              Launch GUI application
    python -m display_presets <command>    Run CLI command

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


def check_dependencies():
    """Check if required dependencies are installed"""
    missing = []

    try:
        import PyQt6
    except ImportError:
        missing.append('PyQt6')

    return missing


def main():
    """Main entry point - routes to GUI or CLI based on arguments"""
    # Check if running in CLI mode (has arguments other than script name)
    cli_commands = ['list', 'apply', 'save', 'delete', 'rename', 'current', 'info', '-h', '--help', '-v', '--version', '-j', '--json']

    is_cli_mode = len(sys.argv) > 1 and (
        sys.argv[1] in cli_commands or
        sys.argv[1].startswith('-')
    )

    if is_cli_mode:
        # CLI mode - minimal dependencies needed
        try:
            from display_presets.cli import run_cli
            sys.exit(run_cli())
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        # GUI mode - full dependencies needed
        missing = check_dependencies()
        if missing:
            print("ERROR: Missing required dependencies!")
            print(f"Missing: {', '.join(missing)}")
            print("\nPlease install dependencies:")
            print("  pip install -r requirements.txt")
            print("\nOr install manually:")
            for pkg in missing:
                print(f"  pip install {pkg}")
            sys.exit(1)

        try:
            from display_presets.tray import TrayApp
            app = TrayApp()
            app.run()
        except Exception as e:
            with open("error.log", "w") as f:
                import traceback
                f.write(traceback.format_exc())
            print(f"Error: {e}")
            print("See error.log for details")
            sys.exit(1)


if __name__ == "__main__":
    main()
