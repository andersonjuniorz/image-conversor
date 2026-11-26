import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
APP_NAME = "image-converter"
EXE_NAME = f"{APP_NAME}.exe" if os.name == "nt" else APP_NAME


# Builds the executable with the same command used by CI.
def build_executable():
    subprocess.run(
        [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm", "--onefile", "--windowed",
            "--name", APP_NAME,
            "--hidden-import", "pillow_jxl",
            "main.py",
        ],
        cwd=ROOT,
        check=True,
    )


# Checks that the executable starts and stays open for a few seconds.
def test_executable_builds_and_starts():
    build_executable()
    exe = ROOT / "dist" / EXE_NAME
    assert exe.exists(), f"executable not found: {exe}"

    env = {**os.environ, "QT_QPA_PLATFORM": "offscreen"}
    proc = subprocess.Popen([str(exe)], env=env)
    try:
        code = proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        # Still running after 8 seconds means it started without crashing.
        proc.terminate()
        proc.wait()
        return
    pytest.fail(f"{EXE_NAME} closed early with exit code {code}")
