import subprocess
import sys

def build():
    print("Building DisplayPresets.exe...")

    try:
        import PyInstaller
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    cmd = [
        "pyinstaller",
        "--onefile",
        "--windowed",
        "--name=DisplayPresets",
        "main.py"
    ]

    subprocess.check_call(cmd)
    print("\nDone! Check dist\\DisplayPresets.exe")

if __name__ == "__main__":
    build()
