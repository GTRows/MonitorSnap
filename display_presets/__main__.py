import sys
import subprocess

def check_dependencies():
    missing = []

    try:
        import PyQt6
    except ImportError:
        missing.append('PyQt6')

    if missing:
        print("ERROR: Missing required dependencies!")
        print(f"Missing: {', '.join(missing)}")
        print("\nPlease install dependencies:")
        print("  pip install -r requirements.txt")
        print("\nOr install manually:")
        for pkg in missing:
            print(f"  pip install {pkg}")
        sys.exit(1)

if __name__ == "__main__":
    check_dependencies()

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
