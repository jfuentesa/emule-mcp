#!/usr/bin/env sh
set -eu
DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PY="$DIR/.venv/bin/python"
[ -x "$PY" ] || PY="$DIR/.venv/Scripts/python.exe"
exec "$PY" -m emule_mcp.server "$@"
