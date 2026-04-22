#!/usr/bin/env python3
"""Validate all JSON entries under entries/{schema,docs,tips}/.

Run locally:        python scripts/validate_entries.py
Run in CI:          same command, exits non-zero on any failure.
Run on single file: python scripts/validate_entries.py path/to/file.json

The validator enforces the minimum schema required by
context_portal/scripts/import_all_entries.py so that broken JSON can
never reach the ConPort database.

Zero third-party dependencies — uses stdlib only.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

# Portable root: this file lives in <repo>/scripts/validate_entries.py
REPO_ROOT = Path(__file__).resolve().parents[1]
ENTRIES_DIR = REPO_ROOT / "entries"

# ---------------------------------------------------------------------------
# Module-code whitelist (keeps schema entries consistent with MODULE_INDEX).
# Extend when a new Ivalua module is introduced.
# ---------------------------------------------------------------------------
VALID_SCHEMA_MODULES = {
    "bas", "sup", "ctr", "req", "rsk", "inv", "spn", "ext",
    "cat", "src", "pur", "com", "pay", "bud", "ord",
}

TIP_ID_RE = re.compile(r"^TIP_[A-Z0-9_]+$")
TABLE_NAME_RE = re.compile(r"^t_[a-z0-9_]+$")


class ValidationError(Exception):
    """Raised for any entry that fails validation."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _require(data: dict, field: str, type_: type, where: str) -> Any:
    if field not in data:
        raise ValidationError(f"{where}: missing required field '{field}'")
    value = data[field]
    if not isinstance(value, type_):
        raise ValidationError(
            f"{where}: field '{field}' must be {type_.__name__}, "
            f"got {type(value).__name__}"
        )
    return value


def _optional(data: dict, field: str, type_: type, where: str) -> Any:
    if field not in data:
        return None
    value = data[field]
    if not isinstance(value, type_):
        raise ValidationError(
            f"{where}: field '{field}' must be {type_.__name__} if present, "
            f"got {type(value).__name__}"
        )
    return value


# ---------------------------------------------------------------------------
# Per-type validators
# ---------------------------------------------------------------------------
def validate_schema(data: dict, where: str) -> None:
    module = _require(data, "module", str, where).strip().lower()
    if module not in VALID_SCHEMA_MODULES:
        raise ValidationError(
            f"{where}: unknown module '{module}'. "
            f"Valid codes: {sorted(VALID_SCHEMA_MODULES)}"
        )

    table = _require(data, "table_technical_name", str, where).strip()
    if not TABLE_NAME_RE.match(table):
        raise ValidationError(
            f"{where}: table_technical_name '{table}' must match {TABLE_NAME_RE.pattern}"
        )

    _optional(data, "table_display_name", str, where)

    columns = _require(data, "columns", list, where)
    if not columns:
        raise ValidationError(f"{where}: 'columns' must not be empty")

    seen_cols: set[str] = set()
    pk_count = 0
    for i, col in enumerate(columns):
        col_where = f"{where} -> columns[{i}]"
        if not isinstance(col, dict):
            raise ValidationError(f"{col_where}: must be an object")
        name = _require(col, "column_name", str, col_where).strip()
        if not name:
            raise ValidationError(f"{col_where}: 'column_name' is empty")
        if name in seen_cols:
            raise ValidationError(f"{col_where}: duplicate column_name '{name}'")
        seen_cols.add(name)
        _require(col, "data_type", str, col_where)
        if col.get("is_primary_key") is True:
            pk_count += 1
    # pk_count == 0 is allowed (views, junction tables...) but warn is harmless

    rels = _optional(data, "relationships", dict, where)
    if rels is not None:
        for fk_side in ("foreign_keys_out", "foreign_keys_in"):
            arr = rels.get(fk_side, [])
            if not isinstance(arr, list):
                raise ValidationError(
                    f"{where}: relationships.{fk_side} must be a list"
                )


def validate_documentation(data: dict, where: str) -> None:
    _require(data, "module", str, where)
    topic = _require(data, "topic", str, where).strip()
    if not topic:
        raise ValidationError(f"{where}: 'topic' must not be empty")
    _optional(data, "file_path", str, where)
    _optional(data, "content_type", str, where)
    _optional(data, "summary", str, where)
    key_concepts = _optional(data, "key_concepts", list, where)
    if key_concepts is not None:
        for i, kc in enumerate(key_concepts):
            if not isinstance(kc, str):
                raise ValidationError(
                    f"{where} -> key_concepts[{i}]: must be a string"
                )
    _optional(data, "content", str, where)
    sections = _optional(data, "sections", list, where)
    if sections is not None:
        for i, sec in enumerate(sections):
            if not isinstance(sec, dict):
                raise ValidationError(f"{where} -> sections[{i}]: must be an object")


def validate_tip(data: dict, where: str) -> None:
    tip_id = _require(data, "tip_id", str, where).strip()
    # Normalize: accept both "TIP_FOO" and "FOO" (import script adds prefix)
    normalized = tip_id if tip_id.startswith("TIP_") else f"TIP_{tip_id}"
    if not TIP_ID_RE.match(normalized):
        raise ValidationError(
            f"{where}: tip_id '{tip_id}' must be UPPER_SNAKE_CASE "
            f"(regex: {TIP_ID_RE.pattern})"
        )
    _require(data, "topic", str, where)
    _require(data, "summary", str, where)
    _require(data, "detail", str, where)
    tags = _optional(data, "tags", list, where)
    if tags is not None:
        for i, t in enumerate(tags):
            if not isinstance(t, str):
                raise ValidationError(f"{where} -> tags[{i}]: must be a string")


VALIDATORS = {
    "schema": validate_schema,
    "docs": validate_documentation,
    "tips": validate_tip,
}

SKIP_FILENAMES = {"template.json", "example.json"}


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------
def _iter_entry_files(target: Path | None) -> list[tuple[str, Path]]:
    """Return list of (subdir_name, path) pairs to validate."""
    out: list[tuple[str, Path]] = []
    if target is not None:
        # Validate a single file — infer subdir from its parent name
        if target.parent.name not in VALIDATORS:
            raise ValidationError(
                f"{target}: parent folder must be one of "
                f"{sorted(VALIDATORS)} (got '{target.parent.name}')"
            )
        out.append((target.parent.name, target))
        return out

    for subdir_name in VALIDATORS:
        subdir = ENTRIES_DIR / subdir_name
        if not subdir.is_dir():
            continue
        for fp in sorted(subdir.glob("*.json")):
            if fp.name in SKIP_FILENAMES or fp.name.startswith("."):
                continue
            out.append((subdir_name, fp))
    return out


def _validate_one(subdir_name: str, fp: Path) -> list[str]:
    """Validate a single file. Returns a list of error messages (empty == OK)."""
    errors: list[str] = []
    rel = fp.relative_to(REPO_ROOT).as_posix()
    try:
        with fp.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
    except json.JSONDecodeError as e:
        return [f"{rel}: invalid JSON ({e.msg} at line {e.lineno}, col {e.colno})"]
    except OSError as e:
        return [f"{rel}: cannot read file ({e})"]

    if not isinstance(data, dict):
        return [f"{rel}: top-level value must be a JSON object, got {type(data).__name__}"]

    validator = VALIDATORS[subdir_name]
    try:
        validator(data, rel)
    except ValidationError as e:
        errors.append(str(e))
    return errors


def main(argv: list[str]) -> int:
    target: Path | None = None
    if len(argv) > 1:
        target = Path(argv[1]).resolve()
        if not target.exists():
            print(f"[FAIL] file not found: {target}", file=sys.stderr)
            return 2

    try:
        files = _iter_entry_files(target)
    except ValidationError as e:
        print(f"[FAIL] {e}", file=sys.stderr)
        return 2

    if not files:
        print("[OK] no user entries to validate (only templates/examples).")
        return 0

    total_errors: list[str] = []
    ok_count = 0
    for subdir_name, fp in files:
        errs = _validate_one(subdir_name, fp)
        if errs:
            total_errors.extend(errs)
        else:
            ok_count += 1

    print(f"Validated {len(files)} file(s): {ok_count} OK, {len(total_errors)} errors.")
    if total_errors:
        print("\nErrors:", file=sys.stderr)
        for err in total_errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("[OK] all entries valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
