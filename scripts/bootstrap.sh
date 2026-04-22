#!/usr/bin/env bash
# -----------------------------------------------------------------------------
# One-shot bootstrap (macOS + Linux).
#
# Runs the full first-run install WITHOUT launching the MCP proxy, so that
# by the time your editor connects, everything is already cached and the
# MCP server starts in < 3 seconds (well under the editor's 60 s timeout).
#
# Does exactly what `conport_launcher.sh` does on first run:
#   1) download portable `uv` binary into .tools/
#   2) `uv` downloads portable CPython
#   3) `uv sync` builds .venv and installs context-portal-mcp + deps
#   4) verifies the ConPort server can be imported
#
# Typical runtime on a fresh machine: 2–5 minutes (network-bound).
# Safe to re-run — it's idempotent.
# -----------------------------------------------------------------------------
set -euo pipefail

# Repo root = parent of scripts/
ROOT="$(cd -P "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[bootstrap] Project root: $ROOT"
echo "[bootstrap] Step 1/4 — ensure launcher is executable"
chmod +x "$ROOT/conport_launcher.sh" 2>/dev/null || true

TOOLS="$ROOT/.tools"
UV_BIN_PATH="$TOOLS/uv"

# ---- detect target triple (must match conport_launcher.sh logic) ----
detect_target() {
  local os arch
  case "$(uname -s)" in
    Darwin) os="apple-darwin" ;;
    Linux)  os="unknown-linux-gnu" ;;
    *) echo "[bootstrap] ERROR: unsupported OS $(uname -s)" >&2; exit 1 ;;
  esac
  case "$(uname -m)" in
    x86_64|amd64) arch="x86_64" ;;
    arm64|aarch64) arch="aarch64" ;;
    *) echo "[bootstrap] ERROR: unsupported arch $(uname -m)" >&2; exit 1 ;;
  esac
  echo "${arch}-${os}"
}

# ---- step 2: portable uv ----
echo "[bootstrap] Step 2/4 — install portable uv binary"
if [ ! -x "$UV_BIN_PATH" ]; then
  mkdir -p "$TOOLS"
  target="$(detect_target)"
  url="https://github.com/astral-sh/uv/releases/latest/download/uv-${target}.tar.gz"
  tmp="$TOOLS/uv.tar.gz"
  echo "[bootstrap]   downloading $url"
  if command -v curl >/dev/null 2>&1; then
    curl -fSL --progress-bar "$url" -o "$tmp"
  elif command -v wget >/dev/null 2>&1; then
    wget --show-progress -q "$url" -O "$tmp"
  else
    echo "[bootstrap] ERROR: need curl or wget" >&2
    exit 1
  fi
  tar -xzf "$tmp" -C "$TOOLS" --strip-components=1 "uv-${target}/uv" 2>/dev/null \
    || tar -xzf "$tmp" -C "$TOOLS" --strip-components=1
  rm -f "$tmp"
  chmod +x "$UV_BIN_PATH"
  echo "[bootstrap]   uv ready: $("$UV_BIN_PATH" --version)"
else
  echo "[bootstrap]   uv already present: $("$UV_BIN_PATH" --version)"
fi

export UV_BIN="$UV_BIN_PATH"
export UV_CACHE_DIR="$TOOLS/uv-cache"
export UV_PYTHON_INSTALL_DIR="$TOOLS/python"

# ---- step 3: resolve Python + install deps ----
echo "[bootstrap] Step 3/4 — install portable Python + project deps (2–5 min)"
"$UV_BIN_PATH" sync --project "$ROOT"

# ---- step 4: smoke test that the conport server imports ----
echo "[bootstrap] Step 4/4 — smoke-test the ConPort server"
"$UV_BIN_PATH" run --project "$ROOT" python -c \
  "import importlib; importlib.import_module('context_portal_mcp'); print('[bootstrap]   context_portal_mcp imported OK')"

echo ""
echo "[bootstrap] DONE. Subsequent launches will start in < 3 seconds."
echo "[bootstrap] You can now point your editor (Windsurf/VS Code/Cursor) at:"
echo "[bootstrap]   $ROOT/conport_launcher.sh"
