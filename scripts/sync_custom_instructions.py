#!/usr/bin/env python3
"""Pull the latest ConPort custom-instruction strategies from upstream.

Fetches the 4 strategy files from
  https://github.com/GreatScottyMac/context-portal/
into ./conport-custom-instructions/*.md and reports what changed.

Exit codes:
  0 = no changes (everything already up to date)
  1 = files were updated  (useful for CI: `if script exits 1, open a PR`)
  2 = network / I/O error

Usage:
    python scripts/sync_custom_instructions.py              # fetch + overwrite
    python scripts/sync_custom_instructions.py --check      # dry-run, only report
    python scripts/sync_custom_instructions.py --ref main   # pin to a branch/tag/sha

Zero third-party dependencies — uses stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEST_DIR = REPO_ROOT / "conport-custom-instructions"

UPSTREAM_OWNER = "GreatScottyMac"
UPSTREAM_REPO = "context-portal"
UPSTREAM_PATH = "conport-custom-instructions"

# (upstream_basename_without_ext, local_filename_with_ext)
FILES = [
    ("cascade_conport_strategy", "cascade_conport_strategy.md"),
    ("generic_conport_strategy", "generic_conport_strategy.md"),
    ("cline_conport_strategy", "cline_conport_strategy.md"),
    ("roo_code_conport_strategy", "roo_code_conport_strategy.md"),
]

USER_AGENT = "ivalua-ai-assistant-sync/1.0"


def _url(ref: str, name: str) -> str:
    return (
        f"https://raw.githubusercontent.com/"
        f"{UPSTREAM_OWNER}/{UPSTREAM_REPO}/{ref}/{UPSTREAM_PATH}/{name}"
    )


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        if resp.status != 200:
            raise urllib.error.HTTPError(
                url, resp.status, f"HTTP {resp.status}", resp.headers, None
            )
        return resp.read()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Dry run: report what would change, don't modify files.",
    )
    parser.add_argument(
        "--ref",
        default="main",
        help="Upstream git ref (branch/tag/commit). Default: main.",
    )
    args = parser.parse_args(argv[1:])

    DEST_DIR.mkdir(parents=True, exist_ok=True)

    changed: list[str] = []
    failed: list[str] = []

    for upstream_name, local_name in FILES:
        url = _url(args.ref, upstream_name)
        try:
            remote = _fetch(url)
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"[FAIL] {upstream_name}: {e}", file=sys.stderr)
            failed.append(local_name)
            continue

        local_path = DEST_DIR / local_name
        if local_path.exists():
            local = local_path.read_bytes()
            if _sha256(local) == _sha256(remote):
                print(f"[ OK ] {local_name} up to date")
                continue
            print(f"[UPD ] {local_name} differs from upstream")
        else:
            print(f"[NEW ] {local_name} does not exist locally")

        changed.append(local_name)
        if not args.check:
            local_path.write_bytes(remote)

    if failed:
        print(f"\n{len(failed)} file(s) failed to download.", file=sys.stderr)
        return 2

    if not changed:
        print("\nAll strategies are up to date.")
        return 0

    mode = "Would update" if args.check else "Updated"
    print(f"\n{mode} {len(changed)} file(s): {', '.join(changed)}")
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
