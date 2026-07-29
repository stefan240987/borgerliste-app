#!/bin/bash
cd "$(dirname "$0")"
export PYTHONUTF8=1

if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    echo "Python er ikke installeret."
    echo "Hent det fra https://www.python.org/downloads/"
    read -r -p "Tryk Enter for at lukke..."
    exit 1
fi

"$PYTHON" setup_and_run.py
