#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repo_root"

command -v uv >/dev/null 2>&1 || {
  printf '%s\n' 'uv is required; install the pinned project toolchain first.' >&2
  exit 1
}

uv sync --locked --python 3.12 --extra dev
uv run --locked --python 3.12 python tools/pivot/preflight.py "$@"
