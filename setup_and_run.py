"""
Starter borgerliste-app lokalt.
Opretter virtuelt miljø og installerer pakker ved første kørsel.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"
APP_FILE = ROOT / "app.py"


def venv_python() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def venv_streamlit() -> Path:
    if sys.platform == "win32":
        return VENV_DIR / "Scripts" / "streamlit.exe"
    return VENV_DIR / "bin" / "streamlit"


def run_command(command: list[str], *, label: str) -> None:
    print(f"\n{label}...")
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        print(f"\nFejl: {label} mislykkedes (kode {result.returncode}).")
        pause_before_exit()
        sys.exit(result.returncode)


def venv_is_valid() -> bool:
    python = venv_python()
    if not python.exists():
        return False
    result = subprocess.run([str(python), "--version"], capture_output=True)
    return result.returncode == 0


def ensure_venv() -> None:
    if venv_is_valid():
        return
    if VENV_DIR.exists():
        print("Opretter nyt Python-miljø til denne computer...")
    else:
        print("Første gang: opretter virtuelt Python-miljø...")
    run_command([sys.executable, "-m", "venv", str(VENV_DIR)], label="Opretter .venv")


def dependencies_installed() -> bool:
    python = venv_python()
    result = subprocess.run(
        [str(python), "-c", "import streamlit, pandas, openpyxl"],
        cwd=ROOT,
        capture_output=True,
    )
    return result.returncode == 0


def ensure_dependencies() -> None:
    if dependencies_installed():
        return
    python = venv_python()
    run_command(
        [str(python), "-m", "pip", "install", "--upgrade", "pip"],
        label="Opdaterer pip",
    )
    run_command(
        [str(python), "-m", "pip", "install", "-r", str(REQUIREMENTS)],
        label="Installerer pakker",
    )


def pause_before_exit() -> None:
    if sys.platform == "win32":
        input("\nTryk Enter for at lukke...")
    else:
        input("\nTryk Enter for at lukke...")


def main() -> None:
    os.chdir(ROOT)

    if not APP_FILE.exists():
        print(f"Kunne ikke finde {APP_FILE}")
        pause_before_exit()
        sys.exit(1)

    print("=" * 60)
    print("  Borgerflow – kontaktopfølgning")
    print("=" * 60)
    print(f"Mappe: {ROOT}")

    try:
        ensure_venv()
        ensure_dependencies()
    except KeyboardInterrupt:
        print("\nAfbrudt.")
        pause_before_exit()
        sys.exit(1)

    streamlit = venv_streamlit()
    python = venv_python()
    if streamlit.exists():
        command = [str(streamlit), "run", str(APP_FILE)]
    else:
        command = [str(python), "-m", "streamlit", "run", str(APP_FILE)]

    print("\nStarter programmet...")
    print("Browseren åbner automatisk på http://localhost:8501")
    print("Luk dette vindue (eller tryk Ctrl+C) for at stoppe programmet.\n")

    try:
        result = subprocess.run(command, cwd=ROOT)
    except KeyboardInterrupt:
        print("\nProgrammet er stoppet.")
        pause_before_exit()
        sys.exit(0)

    if result.returncode != 0:
        print(f"\nProgrammet stoppede med fejl (kode {result.returncode}).")
        pause_before_exit()
        sys.exit(result.returncode)

    pause_before_exit()


if __name__ == "__main__":
    main()
