#!/bin/sh
set -e

VENV_DIR="${APPLE_TV_VENV_DIR:-/data/.venv}"
REQUIREMENTS_HASH_FILE="$VENV_DIR/.requirements.sha256"
PYTHON_VERSION="$(python -V)"
REQUIREMENTS_HASH="$(sha256sum /app/requirements.txt | awk '{print $1}')"
CURRENT_HASH="$PYTHON_VERSION $REQUIREMENTS_HASH"

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "Creating Python virtual environment at $VENV_DIR"
  python -m venv "$VENV_DIR"
fi

INSTALLED_HASH=""

if [ -f "$REQUIREMENTS_HASH_FILE" ]; then
  INSTALLED_HASH="$(cat "$REQUIREMENTS_HASH_FILE")"
fi

if [ "$INSTALLED_HASH" != "$CURRENT_HASH" ]; then
  echo "Installing Python dependencies"
  "$VENV_DIR/bin/python" -m pip install --progress-bar off --upgrade pip
  "$VENV_DIR/bin/python" -m pip install --progress-bar off -r /app/requirements.txt
  printf '%s\n' "$CURRENT_HASH" > "$REQUIREMENTS_HASH_FILE"
else
  echo "Python dependencies are already installed for current requirements."
fi

exec "$VENV_DIR/bin/python" /app/server.py
