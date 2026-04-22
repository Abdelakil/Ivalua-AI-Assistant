"""Module toggle for ConPort Ivalua knowledge base.

Problem: some AI models call mcp0_get_custom_data with category=null and
key=null, which dumps the entire custom_data table (thousands of large
rows, tens of MB) and crashes the IDE/agent.

Mitigation: move selected modules' rows OUT of custom_data into a stash
table (custom_data_stash). ConPort only queries custom_data, so stashed
modules are invisible to every ConPort tool (get_custom_data, FTS,
semantic search). Re-enabling moves them back.

A registry entry DISABLED_MODULES (category CONPORT_CONTROL) tracks the
state so the agent can self-report what's unavailable.

Usage:
    python module_toggle.py status
    python module_toggle.py list-modules
    python module_toggle.py disable <module_code> [<module_code> ...]
    python module_toggle.py enable  <module_code> [<module_code> ...]
    python module_toggle.py disable-all-docs
    python module_toggle.py enable-all

Module codes can be:
  - Schema modules (lowercase 3-4 letter): bas, sup, ctr, req, ...
  - Doc module slugs (UPPERCASE): SUPPLIER_MANAGEMENT_V176_V178, SOURCING, ...
  - Or special tokens: 'ALL_DOCS', 'ALL_SCHEMA'
"""
from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
DB = WORKSPACE / "context_portal" / "context.db"

STASH_TABLE = "custom_data_stash"
CONTROL_CATEGORY = "CONPORT_CONTROL"
REGISTRY_KEY = "DISABLED_MODULES"
SAFETY_KEY = "SAFETY_README"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_stash(conn: sqlite3.Connection) -> None:
    conn.executescript(f"""
    CREATE TABLE IF NOT EXISTS {STASH_TABLE} (
        id INTEGER PRIMARY KEY,
        stashed_at DATETIME NOT NULL,
        module_token VARCHAR(255) NOT NULL,
        original_timestamp DATETIME NOT NULL,
        category VARCHAR(255) NOT NULL,
        key VARCHAR(255) NOT NULL,
        value TEXT NOT NULL,
        UNIQUE (category, key)
    );
    CREATE INDEX IF NOT EXISTS ix_{STASH_TABLE}_module
        ON {STASH_TABLE} (module_token);
    """)
    conn.commit()


# ---------- Pattern selection ----------

def patterns_for(module_token: str) -> list[tuple[str, str]]:
    """Return list of (category, key GLOB) pairs for a given module token."""
    t = module_token.strip()
    patterns: list[tuple[str, str]] = []

    if t.upper() == "ALL_SCHEMA":
        patterns.append(("Database_Schema", "*"))
        return patterns
    if t.upper() == "ALL_DOCS":
        patterns.append(("IVALUA_Documentation", "*"))
        return patterns

    # Schema module (short lowercase code, e.g. 'bas', 'sup')
    if t.islower() or (len(t) <= 5 and "_" not in t):
        code = t.lower()
        patterns.append(("Database_Schema", f"TABLE_{code.upper()}_*"))
        patterns.append(("Database_Schema", f"MODULE_{code.upper()}"))

    # Doc module slug (uppercase with underscores)
    patterns.append(("IVALUA_Documentation", f"DOC_{t.upper()}_*"))
    patterns.append(("IVALUA_Documentation", f"DOC_INDEX_{t.upper()}"))

    return patterns


def matching_rows(cur: sqlite3.Cursor, module_token: str, source: str):
    """Return list of (id, timestamp, category, key, value) from source table."""
    ts_col = "original_timestamp" if source == STASH_TABLE else "timestamp"
    results = []
    for cat, glob in patterns_for(module_token):
        cur.execute(
            f"SELECT id, {ts_col}, category, key, value FROM {source} "
            f"WHERE category = ? AND key GLOB ?",
            (cat, glob),
        )
        results.extend(cur.fetchall())
    # Deduplicate by (category, key)
    seen = set()
    unique = []
    for r in results:
        k = (r[2], r[3])
        if k not in seen:
            seen.add(k)
            unique.append(r)
    return unique


# ---------- Operations ----------

def disable(conn: sqlite3.Connection, tokens: list[str]) -> None:
    ensure_stash(conn)
    cur = conn.cursor()
    total = 0
    for token in tokens:
        rows = matching_rows(cur, token, "custom_data")
        if not rows:
            print(f"  {token}: no matching rows in custom_data")
            continue
        stash_rows = [
            (now_iso(), token, r[1], r[2], r[3], r[4]) for r in rows
        ]
        cur.executemany(
            f"INSERT OR REPLACE INTO {STASH_TABLE} "
            f"(stashed_at, module_token, original_timestamp, category, key, value) "
            f"VALUES (?, ?, ?, ?, ?, ?)",
            stash_rows,
        )
        # Delete from live (triggers handle FTS removal)
        ids = [r[0] for r in rows]
        cur.executemany("DELETE FROM custom_data WHERE id = ?", [(i,) for i in ids])
        conn.commit()
        print(f"  {token}: stashed {len(rows)} rows")
        total += len(rows)
    print(f"Total stashed: {total}")
    update_registry(conn)


def enable(conn: sqlite3.Connection, tokens: list[str]) -> None:
    ensure_stash(conn)
    cur = conn.cursor()
    total = 0
    for token in tokens:
        rows = matching_rows(cur, token, STASH_TABLE)
        if not rows:
            print(f"  {token}: no stashed rows")
            continue
        live_rows = [(r[1], r[2], r[3], r[4]) for r in rows]
        cur.executemany(
            "INSERT OR REPLACE INTO custom_data (timestamp, category, key, value) "
            "VALUES (?, ?, ?, ?)",
            live_rows,
        )
        ids = [r[0] for r in rows]
        cur.executemany(f"DELETE FROM {STASH_TABLE} WHERE id = ?", [(i,) for i in ids])
        conn.commit()
        print(f"  {token}: restored {len(rows)} rows")
        total += len(rows)
    print(f"Total restored: {total}")
    update_registry(conn)


def status(conn: sqlite3.Connection) -> None:
    ensure_stash(conn)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*), category FROM custom_data GROUP BY category")
    print("ACTIVE (custom_data):")
    for n, cat in cur.fetchall():
        print(f"  {cat}: {n}")
    cur.execute(
        f"SELECT module_token, COUNT(*) FROM {STASH_TABLE} GROUP BY module_token "
        f"ORDER BY module_token"
    )
    stashed = cur.fetchall()
    print("\nDISABLED (stashed):")
    if not stashed:
        print("  (none)")
    else:
        for token, n in stashed:
            print(f"  {token}: {n} rows")


def list_modules(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        "SELECT json_extract(value, '$.modules') FROM custom_data "
        "WHERE category = 'Database_Schema' AND key = 'MODULE_INDEX'"
    )
    row = cur.fetchone()
    schema_mods = json.loads(row[0]) if row and row[0] else []
    cur.execute(
        "SELECT json_extract(value, '$.modules') FROM custom_data "
        "WHERE category = 'IVALUA_Documentation' AND key = 'DOC_INDEX_ALL'"
    )
    row = cur.fetchone()
    doc_mods = json.loads(row[0]) if row and row[0] else []

    # Also check stash for master indexes (in case disabled)
    ensure_stash(conn)
    cur.execute(
        f"SELECT json_extract(value, '$.modules') FROM {STASH_TABLE} "
        f"WHERE category = 'Database_Schema' AND key = 'MODULE_INDEX'"
    )
    row = cur.fetchone()
    if row and row[0]:
        schema_mods = schema_mods or json.loads(row[0])
    cur.execute(
        f"SELECT json_extract(value, '$.modules') FROM {STASH_TABLE} "
        f"WHERE category = 'IVALUA_Documentation' AND key = 'DOC_INDEX_ALL'"
    )
    row = cur.fetchone()
    if row and row[0]:
        doc_mods = doc_mods or json.loads(row[0])

    print(f"Schema modules ({len(schema_mods)}):")
    print("  " + ", ".join(schema_mods))
    print(f"\nDocumentation modules ({len(doc_mods)}):")
    for m in doc_mods:
        print(f"  {m}")


def update_registry(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        f"SELECT module_token, category, COUNT(*) FROM {STASH_TABLE} "
        f"GROUP BY module_token, category ORDER BY module_token, category"
    )
    entries: dict[str, dict] = {}
    for token, cat, n in cur.fetchall():
        entries.setdefault(token, {"by_category": {}})
        entries[token]["by_category"][cat] = n

    registry = {
        "description": (
            "Modules physically removed from custom_data and stashed in "
            "custom_data_stash. These modules are INVISIBLE to ConPort queries "
            "(get_custom_data, FTS, semantic search). To restore, run: "
            "python context_portal/scripts/module_toggle.py enable <token>"
        ),
        "disabled_modules": entries,
        "total_disabled": len(entries),
        "total_stashed_rows": sum(
            sum(v.values()) for v in [e["by_category"] for e in entries.values()]
        ),
        "updated": now_iso(),
    }
    cur.execute(
        "INSERT OR REPLACE INTO custom_data (timestamp, category, key, value) "
        "VALUES (?, ?, ?, ?)",
        (now_iso(), CONTROL_CATEGORY, REGISTRY_KEY,
         json.dumps(registry, ensure_ascii=False)),
    )
    # Also maintain a safety README so AIs querying CONPORT_CONTROL see the rules
    safety = {
        "critical_rules": [
            "NEVER call mcp0_get_custom_data with category=null or key=null. "
            "The custom_data table holds 3000+ large rows (tens of MB) and will crash the IDE.",
            "ALWAYS pass BOTH category AND key.",
            "For discovery, use category='Database_Schema' key='MODULE_INDEX' "
            "or category='IVALUA_Documentation' key='DOC_INDEX_ALL'.",
            "For fuzzy lookup, use mcp0_search_custom_data_value_fts with a category_filter.",
            "For semantic search, ALWAYS pass filter_custom_data_categories to avoid mixing schema and docs.",
            "Check CONPORT_CONTROL/DISABLED_MODULES to know which modules are currently unavailable.",
        ],
        "known_categories": ["Database_Schema", "IVALUA_Documentation", "CONPORT_CONTROL"],
        "registry_location": {"category": CONTROL_CATEGORY, "key": REGISTRY_KEY},
        "updated": now_iso(),
    }
    cur.execute(
        "INSERT OR REPLACE INTO custom_data (timestamp, category, key, value) "
        "VALUES (?, ?, ?, ?)",
        (now_iso(), CONTROL_CATEGORY, SAFETY_KEY,
         json.dumps(safety, ensure_ascii=False)),
    )
    conn.commit()


# ---------- CLI ----------

def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    cmd = argv[0]
    args = argv[1:]

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL")

    if cmd == "status":
        status(conn)
    elif cmd == "list-modules":
        list_modules(conn)
    elif cmd == "disable":
        if not args:
            print("error: need at least one module token")
            return 2
        disable(conn, args)
    elif cmd == "enable":
        if not args:
            print("error: need at least one module token")
            return 2
        enable(conn, args)
    elif cmd == "disable-all-docs":
        disable(conn, ["ALL_DOCS"])
    elif cmd == "enable-all":
        # Restore every stashed module_token
        ensure_stash(conn)
        cur = conn.cursor()
        cur.execute(f"SELECT DISTINCT module_token FROM {STASH_TABLE}")
        tokens = [r[0] for r in cur.fetchall()]
        if tokens:
            enable(conn, tokens)
        else:
            print("Nothing stashed.")
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
        return 2

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
