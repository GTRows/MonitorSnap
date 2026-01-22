"""
MonitorSnap CLI - Command line interface for display preset management.

Usage:
    monitorsnap list                    List all saved presets
    monitorsnap apply <name>            Apply a preset
    monitorsnap save <name>             Save current display config as preset
    monitorsnap delete <name>           Delete a preset
    monitorsnap rename <old> <new>      Rename a preset
    monitorsnap current                 Show current display configuration
    monitorsnap info <name>             Show detailed preset information
    monitorsnap --version               Show version
    monitorsnap --help                  Show help
"""

import argparse
import sys
import json
from typing import Optional


def get_version():
    return "1.0.0"


def create_parser():
    parser = argparse.ArgumentParser(
        prog="monitorsnap",
        description="MonitorSnap - Save and restore Windows display configurations",
        epilog="Examples:\n"
               "  monitorsnap list\n"
               "  monitorsnap apply \"Gaming Setup\"\n"
               "  monitorsnap save \"Work Mode\"\n"
               "  monitorsnap current\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"MonitorSnap {get_version()}"
    )

    parser.add_argument(
        "--json", "-j",
        action="store_true",
        help="Output in JSON format (for scripting)"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list command
    list_parser = subparsers.add_parser("list", help="List all saved presets")
    list_parser.add_argument(
        "--detailed", "-d",
        action="store_true",
        help="Show detailed information for each preset"
    )

    # apply command
    apply_parser = subparsers.add_parser("apply", help="Apply a saved preset")
    apply_parser.add_argument("name", help="Name of the preset to apply")

    # save command
    save_parser = subparsers.add_parser("save", help="Save current display configuration")
    save_parser.add_argument("name", help="Name for the new preset")
    save_parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite if preset already exists"
    )

    # delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a preset")
    delete_parser.add_argument("name", help="Name of the preset to delete")
    delete_parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Skip confirmation prompt"
    )

    # rename command
    rename_parser = subparsers.add_parser("rename", help="Rename a preset")
    rename_parser.add_argument("old_name", help="Current preset name")
    rename_parser.add_argument("new_name", help="New preset name")

    # current command
    subparsers.add_parser("current", help="Show current display configuration")

    # info command
    info_parser = subparsers.add_parser("info", help="Show detailed preset information")
    info_parser.add_argument("name", help="Name of the preset")

    return parser


def print_error(message: str, json_output: bool = False):
    """Print error message"""
    if json_output:
        print(json.dumps({"success": False, "error": message}))
    else:
        print(f"Error: {message}", file=sys.stderr)


def print_success(message: str, data: Optional[dict] = None, json_output: bool = False):
    """Print success message"""
    if json_output:
        result = {"success": True, "message": message}
        if data:
            result["data"] = data
        print(json.dumps(result, indent=2))
    else:
        print(message)


def cmd_list(args):
    """List all presets"""
    from display_presets.preset_service import PresetService

    presets = PresetService()
    names = presets.list_names()

    if args.json:
        if args.detailed:
            detailed = []
            for name in names:
                try:
                    data = presets.load(name)
                    config = data.get('config', {})
                    paths = config.get('paths', [])
                    active_monitors = sum(1 for p in paths if p.get('targetInfo', {}).get('targetAvailable'))
                    detailed.append({
                        "name": name,
                        "monitors": active_monitors,
                        "hotkey": data.get('hotkey'),
                        "created_at": data.get('created_at')
                    })
                except:
                    detailed.append({"name": name, "error": "Could not load"})
            print(json.dumps({"success": True, "presets": detailed}, indent=2))
        else:
            print(json.dumps({"success": True, "presets": names}, indent=2))
        return 0

    if not names:
        print("No presets saved yet.")
        print("\nUse 'monitorsnap save <name>' to save your current display configuration.")
        return 0

    print(f"Saved Presets ({len(names)}):")
    print("-" * 40)

    if args.detailed:
        for name in names:
            try:
                data = presets.load(name)
                config = data.get('config', {})
                paths = config.get('paths', [])
                active_monitors = sum(1 for p in paths if p.get('targetInfo', {}).get('targetAvailable'))
                hotkey = data.get('hotkey', '-')
                created = data.get('created_at', 'Unknown')[:10] if data.get('created_at') else 'Unknown'
                print(f"  {name}")
                print(f"    Monitors: {active_monitors}  |  Hotkey: {hotkey or '-'}  |  Created: {created}")
            except Exception as e:
                print(f"  {name} (error loading)")
    else:
        for name in names:
            print(f"  - {name}")

    return 0


def cmd_apply(args):
    """Apply a preset"""
    from display_presets.preset_service import PresetService
    from display_presets.display_config import DisplayConfigManager

    presets = PresetService()
    display = DisplayConfigManager()

    try:
        data = presets.load(args.name)
        config = data['config']
        result = display.apply(config)

        if result == 0:
            print_success(f"Preset '{args.name}' applied successfully.", json_output=args.json)
            return 0
        else:
            print_error(f"Failed to apply preset '{args.name}'. Error code: {result}", args.json)
            return 1
    except FileNotFoundError:
        print_error(f"Preset '{args.name}' not found.", args.json)
        return 1
    except Exception as e:
        print_error(f"Failed to apply preset: {e}", args.json)
        return 1


def cmd_save(args):
    """Save current display configuration"""
    from display_presets.preset_service import PresetService
    from display_presets.display_config import DisplayConfigManager

    presets = PresetService()
    display = DisplayConfigManager()

    # Check if preset already exists
    existing = presets.list_names()
    if args.name in existing and not args.force:
        print_error(f"Preset '{args.name}' already exists. Use --force to overwrite.", args.json)
        return 1

    try:
        config = display.get_current()
        presets.save(args.name, config)
        print_success(f"Preset '{args.name}' saved successfully.", json_output=args.json)
        return 0
    except Exception as e:
        print_error(f"Failed to save preset: {e}", args.json)
        return 1


def cmd_delete(args):
    """Delete a preset"""
    from display_presets.preset_service import PresetService

    presets = PresetService()

    # Confirmation
    if not args.yes and not args.json:
        response = input(f"Are you sure you want to delete '{args.name}'? [y/N] ")
        if response.lower() not in ('y', 'yes'):
            print("Cancelled.")
            return 0

    try:
        presets.delete(args.name)
        print_success(f"Preset '{args.name}' deleted.", json_output=args.json)
        return 0
    except FileNotFoundError:
        print_error(f"Preset '{args.name}' not found.", args.json)
        return 1
    except Exception as e:
        print_error(f"Failed to delete preset: {e}", args.json)
        return 1


def cmd_rename(args):
    """Rename a preset"""
    from display_presets.preset_service import PresetService

    presets = PresetService()

    try:
        presets.rename(args.old_name, args.new_name)
        print_success(f"Preset renamed from '{args.old_name}' to '{args.new_name}'.", json_output=args.json)
        return 0
    except FileNotFoundError:
        print_error(f"Preset '{args.old_name}' not found.", args.json)
        return 1
    except FileExistsError:
        print_error(f"Preset '{args.new_name}' already exists.", args.json)
        return 1
    except Exception as e:
        print_error(f"Failed to rename preset: {e}", args.json)
        return 1


def cmd_current(args):
    """Show current display configuration"""
    from display_presets.display_config import DisplayConfigManager

    display = DisplayConfigManager()

    try:
        config = display.get_current()
        paths = config.get('paths', [])
        modes = config.get('modes', [])

        monitors = []
        for path in paths:
            if not path.get('targetInfo', {}).get('targetAvailable'):
                continue

            source_idx = path.get('sourceInfo', {}).get('modeInfoIdx')
            if source_idx is None or source_idx >= len(modes):
                continue

            mode = modes[source_idx]
            if mode.get('infoType') != 1:
                continue

            source_mode = mode.get('sourceMode', {})
            pos = source_mode.get('position', {})
            width = source_mode.get('width', 0)
            height = source_mode.get('height', 0)

            # Check for primary flag
            is_primary = bool(path.get('flags', 0) & 0x1)

            monitors.append({
                'position': {'x': pos.get('x', 0), 'y': pos.get('y', 0)},
                'resolution': {'width': width, 'height': height},
                'primary': is_primary
            })

        if args.json:
            print(json.dumps({
                "success": True,
                "monitors": monitors,
                "total": len(monitors)
            }, indent=2))
        else:
            print(f"Current Display Configuration ({len(monitors)} monitors):")
            print("-" * 50)

            # Sort by position
            monitors_sorted = sorted(monitors, key=lambda m: (m['position']['y'], m['position']['x']))

            for i, mon in enumerate(monitors_sorted, 1):
                primary_str = " (Primary)" if mon['primary'] else ""
                print(f"  Monitor {i}{primary_str}:")
                print(f"    Resolution: {mon['resolution']['width']}x{mon['resolution']['height']}")
                print(f"    Position:   ({mon['position']['x']}, {mon['position']['y']})")

        return 0
    except Exception as e:
        print_error(f"Failed to get current configuration: {e}", args.json)
        return 1


def cmd_info(args):
    """Show detailed preset information"""
    from display_presets.preset_service import PresetService

    presets = PresetService()

    try:
        data = presets.load(args.name)
        config = data.get('config', {})
        paths = config.get('paths', [])
        modes = config.get('modes', [])

        monitors = []
        for path in paths:
            if not path.get('targetInfo', {}).get('targetAvailable'):
                continue

            source_idx = path.get('sourceInfo', {}).get('modeInfoIdx')
            if source_idx is None or source_idx >= len(modes):
                continue

            mode = modes[source_idx]
            if mode.get('infoType') != 1:
                continue

            source_mode = mode.get('sourceMode', {})
            pos = source_mode.get('position', {})
            width = source_mode.get('width', 0)
            height = source_mode.get('height', 0)
            is_primary = bool(path.get('flags', 0) & 0x1)

            monitors.append({
                'position': {'x': pos.get('x', 0), 'y': pos.get('y', 0)},
                'resolution': {'width': width, 'height': height},
                'primary': is_primary
            })

        if args.json:
            print(json.dumps({
                "success": True,
                "name": args.name,
                "hotkey": data.get('hotkey'),
                "created_at": data.get('created_at'),
                "monitors": monitors
            }, indent=2))
        else:
            print(f"Preset: {args.name}")
            print("=" * 50)
            print(f"  Hotkey:     {data.get('hotkey') or 'Not set'}")
            print(f"  Created:    {data.get('created_at', 'Unknown')}")
            print(f"  Monitors:   {len(monitors)}")
            print()
            print("Monitor Configuration:")
            print("-" * 50)

            monitors_sorted = sorted(monitors, key=lambda m: (m['position']['y'], m['position']['x']))
            for i, mon in enumerate(monitors_sorted, 1):
                primary_str = " (Primary)" if mon['primary'] else ""
                print(f"  Monitor {i}{primary_str}:")
                print(f"    Resolution: {mon['resolution']['width']}x{mon['resolution']['height']}")
                print(f"    Position:   ({mon['position']['x']}, {mon['position']['y']})")

        return 0
    except FileNotFoundError:
        print_error(f"Preset '{args.name}' not found.", args.json)
        return 1
    except Exception as e:
        print_error(f"Failed to load preset info: {e}", args.json)
        return 1


def run_cli(args=None):
    """Main CLI entry point"""
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    if not parsed_args.command:
        parser.print_help()
        return 0

    commands = {
        'list': cmd_list,
        'apply': cmd_apply,
        'save': cmd_save,
        'delete': cmd_delete,
        'rename': cmd_rename,
        'current': cmd_current,
        'info': cmd_info,
    }

    cmd_func = commands.get(parsed_args.command)
    if cmd_func:
        return cmd_func(parsed_args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(run_cli())
