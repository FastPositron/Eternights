"""
Build the installer .exe using PyInstaller.
Embeds translation JSON data inside the executable.
"""
import subprocess
import sys
import shutil
from pathlib import Path

PYTHON = sys.executable
ROOT = Path(__file__).parent
OUTPUT = ROOT / "output"
DIST = ROOT / "dist"

# Data files to embed
DATA_FILES = [
    OUTPUT / "existing_translations.json",
    OUTPUT / "ui_strings_ru.json",
]

# Verify all data files exist
for f in DATA_FILES:
    if not f.exists():
        print(f"ERROR: Missing {f}")
        sys.exit(1)
    print(f"  {f.name}: {f.stat().st_size:,} bytes")

# Build the add-data arguments
add_data = []
for f in DATA_FILES:
    add_data.extend(["--add-data", f"{f};data"])

cmd = [
    PYTHON, "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--name", "Eternights_Russian",
    "--clean",
    *add_data,
    str(ROOT / "install_rus.py"),
]

print(f"\nRunning: {' '.join(cmd)}")
result = subprocess.run(cmd, cwd=str(ROOT))

if result.returncode == 0:
    exe = DIST / "Eternights_Russian.exe"
    if exe.exists():
        print(f"\nSUCCESS! {exe}")
        print(f"Size: {exe.stat().st_size / 1024 / 1024:.1f} MB")
    else:
        print("Build succeeded but .exe not found?")
else:
    print(f"\nBuild FAILED with code {result.returncode}")
