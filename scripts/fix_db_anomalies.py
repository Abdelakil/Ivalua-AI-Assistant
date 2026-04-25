"""Fix known DB anomalies:
1. Remove TIPS_INDEX orphan (not part of entries/ pipeline, inconsistent key format).
2. Remove extraction-error entries (content = '[DOCX/PDF/PPTX extraction error: ...]').
3. Rebuild FTS after deletions.

Run: python scripts/fix_db_anomalies.py
"""
import sqlite3
import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

WORKSPACE = Path(__file__).resolve().parents[1]
DB = WORKSPACE / "context_portal" / "context.db"


def main():
    log.info("Opening DB: %s", DB)
    conn = sqlite3.connect(DB)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()

    # 1. Remove TIPS_INDEX orphan
    cur.execute("SELECT COUNT(*) FROM custom_data WHERE category='Tips' AND key='TIPS_INDEX'")
    if cur.fetchone()[0]:
        cur.execute("DELETE FROM custom_data WHERE category='Tips' AND key='TIPS_INDEX'")
        conn.commit()
        log.info("Deleted TIPS_INDEX orphan from Tips category.")
    else:
        log.info("TIPS_INDEX not found — already clean.")

    # 2. Remove extraction-error entries (content starts with '[' + error pattern)
    cur.execute(
        "SELECT key, value FROM custom_data WHERE category='IVALUA_Documentation' "
        "AND key NOT LIKE 'DOC_INDEX_%'"
    )
    error_keys = []
    for key, val in cur.fetchall():
        try:
            v = json.loads(val)
            content = v.get("content", "")
            if content.startswith("[") and "extraction error" in content:
                error_keys.append(key)
        except Exception:
            pass

    if error_keys:
        log.info("Found %d extraction-error entries to remove: %s", len(error_keys), error_keys)
        cur.executemany(
            "DELETE FROM custom_data WHERE category='IVALUA_Documentation' AND key=?",
            [(k,) for k in error_keys],
        )
        conn.commit()
        log.info("Deleted extraction-error entries.")
    else:
        log.info("No extraction-error entries found.")

    # 3. Verify counts
    cur.execute("SELECT category, COUNT(*) FROM custom_data GROUP BY category ORDER BY category")
    log.info("DB state after cleanup:")
    for cat, cnt in cur.fetchall():
        log.info("  %s: %d", cat, cnt)

    # 4. Rebuild FTS to stay in sync after deletes
    cur.execute("SELECT COUNT(*) FROM custom_data")
    cd_count = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM custom_data_fts")
    fts_count = cur.fetchone()[0]

    if cd_count != fts_count:
        log.info("FTS out of sync (cd=%d, fts=%d) — rebuilding...", cd_count, fts_count)
        cur.execute("DELETE FROM custom_data_fts")
        conn.commit()
        cur.execute("SELECT id, category, key, value FROM custom_data")
        rows = cur.fetchall()
        cur.executemany(
            "INSERT INTO custom_data_fts (rowid, category, key, value_text) VALUES (?, ?, ?, ?)",
            rows,
        )
        conn.commit()
        conn.execute("INSERT INTO custom_data_fts(custom_data_fts) VALUES('optimize')")
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM custom_data_fts")
        log.info("FTS rebuilt: %d rows.", cur.fetchone()[0])
    else:
        log.info("FTS already in sync (%d rows).", fts_count)

    conn.close()
    log.info("Done.")


if __name__ == "__main__":
    main()
