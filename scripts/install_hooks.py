#!/usr/bin/env python3
"""Install the repo's git hooks (one-time, per clone).

Sets `core.hooksPath` to `.githooks/` so every commit validates staged
entries via `scripts/validate_entries.py`.

Usage:
    python scripts/install_hooks.py          # install
    python scripts/install_hooks.py --uninstall

Zero third-party deps. Works on Windows, macOS, Linux.
"""
from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_DIR = REPO_ROOT / ".githooks"


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            f"[install_hooks] command failed: {' '.join(cmd)}\n{result.stderr}"
        )
    return result.stdout.strip()


def install() -> None:
    if not (REPO_ROOT / ".git").exists():
        raise SystemExit("[install_hooks] this folder is not a git repo yet. Run `git init` first.")
    if not HOOKS_DIR.is_dir():
        raise SystemExit(f"[install_hooks] hooks dir missing: {HOOKS_DIR}")

    run(["git", "config", "core.hooksPath", ".githooks"])

    # Ensure hook scripts are executable on Unix (Windows git-bash ignores mode bits).
    for hook in HOOKS_DIR.iterdir():
        if hook.is_file():
            hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print("[install_hooks] OK — git hooks installed (core.hooksPath=.githooks).")
    print("[install_hooks] Bypass once with: git commit --no-verify")


def uninstall() -> None:
    run(["git", "config", "--unset", "core.hooksPath"])
    print("[install_hooks] OK — hooks uninstalled.")


def main(argv: list[str]) -> int:
    if "--uninstall" in argv:
        uninstall()
    else:
        install()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
