#!/usr/bin/env bash
# ==============================================================================
# Portable ConPort launcher (macOS + Linux) - plug & play, no admin rights.
#
# On first run:
#   1) Downloads a standalone `uv` binary into .tools/ (no installer, no sudo).
#   2) `uv` auto-downloads a portable CPython into the user cache on first use.
#   3) `uv run` builds a project-local .venv from pyproject.toml and installs
#      context-portal-mcp + deps (no admin rights needed).
#   4) Launches the safety proxy, which spawns conport-mcp as a child.
#
# On subsequent runs: everything is cached, startup is near-instant.
#
# Point your MCP client at this script. Example mcp_config.json entry:
#   {
#     "conport": {
#       "command": "/absolute/path/to/project/conport_launcher.sh",
#       "disabled": false
#     }
#   }
# ==============================================================================
set -euo pipefail

# Resolve project root (directory containing this script) - follow symlinks.
_src="${BASH_SOURCE[0]}"
while [ -L "$_src" ]; do
  _dir="$(cd -P "$(dirname "$_src")" && pwd)"
  _src="$(readlink "$_src")"
  [[ "$_src" != /* ]] && _src="$_dir/$_src"
done
ROOT="$(cd -P "$(dirname "$_src")" && pwd)"

TOOLS="$ROOT/.tools"
UV_BIN_PATH="$TOOLS/uv"
PROXY="$ROOT/context_portal/scripts/conport_safe_proxy.py"

log() { printf '[conport_launcher] %s\n' "$*" >&2; }

# ---- Detect OS + CPU arch, pick the right uv release ------------------------
detect_target() {
  local os arch
  case "$(uname -s)" in
    Darwin) os="apple-darwin" ;;
    Linux)  os="unknown-linux-gnu" ;;
    *) log "ERROR: unsupported OS $(uname -s)"; exit 1 ;;
  esac
  case "$(uname -m)" in
    x86_64|amd64) arch="x86_64" ;;
    arm64|aarch64) arch="aarch64" ;;
    *) log "ERROR: unsupported arch $(uname -m)"; exit 1 ;;
  esac
  echo "${arch}-${os}"
}

# ---- Bootstrap uv on first run ----------------------------------------------
if [ ! -x "$UV_BIN_PATH" ]; then
  log "First run: downloading portable uv..."
  mkdir -p "$TOOLS"
  target="$(detect_target)"
  url="https://github.com/astral-sh/uv/releases/latest/download/uv-${target}.tar.gz"
  tmp="$TOOLS/uv.tar.gz"
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$url" -o "$tmp"
  elif command -v wget >/dev/null 2>&1; then
    wget -q "$url" -O "$tmp"
  else
    log "ERROR: need curl or wget to bootstrap uv"
    exit 1
  fi
  tar -xzf "$tmp" -C "$TOOLS" --strip-components=1 "uv-${target}/uv" 2>/dev/null \
    || tar -xzf "$tmp" -C "$TOOLS" --strip-components=1
  rm -f "$tmp"
  chmod +x "$UV_BIN_PATH"
  if [ ! -x "$UV_BIN_PATH" ]; then
    log "ERROR: uv binary not found after extraction"
    exit 1
  fi
  log "uv ready at $UV_BIN_PATH"
fi

# Tell the proxy to spawn conport-mcp via our bundled uv.
export UV_BIN="$UV_BIN_PATH"

# Keep uv / Python / pip caches project-local (fully self-contained folder).
export UV_CACHE_DIR="$TOOLS/uv-cache"
export UV_PYTHON_INSTALL_DIR="$TOOLS/python"

# ---- Run the proxy via uv (handles venv + deps automatically) ---------------
exec "$UV_BIN_PATH" run --project "$ROOT" python "$PROXY"
