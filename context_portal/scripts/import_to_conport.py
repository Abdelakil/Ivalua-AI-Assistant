"""Direct SQLite importer for ConPort custom_data.

Reads chunk JSONs from context_portal/import_data/ and inserts via
INSERT OR REPLACE on (category, key). FTS is kept in sync via the
existing triggers on custom_data. Vector embeddings will be regenerated
by the ConPort server on semantic search requests.
"""
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
DB = WORKSPACE / "context_portal" / "context.db"


def import_chunks(pattern="schema_chunk_*.json", import_dir=None):
    import_dir = import_dir or WORKSPACE / "context_portal" / "import_data"
    files = sorted(import_dir.glob(pattern))
    if not files:
        print(f"No files matching {pattern} in {import_dir}")
        return

    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()

    total = 0
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            items = json.load(f)
        rows = []
        ts = datetime.utcnow().isoformat()
        for item in items:
            rows.append((
                ts,
                item["category"],
                item["key"],
                json.dumps(item["value"], ensure_ascii=False),
            ))
        # Use INSERT OR REPLACE to upsert on (category, key)
        # But REPLACE deletes+inserts, firing delete+insert triggers (correct FTS behavior).
        cur.executemany(
            "INSERT OR REPLACE INTO custom_data (timestamp, category, key, value) VALUES (?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        total += len(rows)
        print(f"  {fp.name}: +{len(rows)} (total: {total})")

    # Verify
    cur.execute("SELECT COUNT(*) FROM custom_data")
    db_total = cur.fetchone()[0]
    cur.execute(
        "SELECT category, COUNT(*) FROM custom_data GROUP BY category ORDER BY category"
    )
    by_cat = cur.fetchall()
    print(f"\nDB total custom_data rows: {db_total}")
    print("By category:")
    for cat, n in by_cat:
        print(f"  {cat}: {n}")

    conn.close()


if __name__ == "__main__":
    pattern = sys.argv[1] if len(sys.argv) > 1 else "schema_chunk_*.json"
    import_chunks(pattern)
