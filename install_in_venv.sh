#!/usr/bin/env bash
set -euo pipefail

VENV_DIR="${1:-.venv}"
PY_BIN="$VENV_DIR/bin/python"

echo "Using venv path: $VENV_DIR"

# create venv if missing
if [ ! -d "$VENV_DIR" ]; then
	echo "Creating virtualenv at $VENV_DIR..."
	python3 -m venv "$VENV_DIR"
fi

# ensure pip is up-to-date for that interpreter
echo "Upgrading pip for $PY_BIN..."
"$PY_BIN" -m pip install --upgrade pip

# install aiohttp into the venv
echo "Installing aiohttp into $VENV_DIR..."
"$PY_BIN" -m pip install aiohttp

# show installation summary
echo "aiohttp installation info:"
"$PY_BIN" -m pip show aiohttp || true

echo
echo "Done. In VS Code select interpreter: $PY_BIN (Ctrl+Shift+P -> 'Python: Select Interpreter')."
echo "Test import with: $PY_BIN -c \"import aiohttp; print('aiohttp ok', aiohttp.__file__)\""
