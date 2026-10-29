#!/bin/bash
# Run the built local web game; never start a development/reload server.
set -euo pipefail
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
if [[ -x "$SCRIPT_DIR/Bowl-Bound" ]]; then
    exec "$SCRIPT_DIR/Bowl-Bound" "$@"
fi
if [[ -x "$SCRIPT_DIR/.venv/bin/python" ]]; then
    PYTHON="$SCRIPT_DIR/.venv/bin/python"
else
    PYTHON="${PYTHON:-python3}"
fi
if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "Python is missing. Use a standalone download, or install Python for the source version." >&2
    exit 1
fi
exec "$PYTHON" -m backend.launcher "$@"
