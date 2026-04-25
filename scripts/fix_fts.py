"""Rebuild the FTS index to re-sync it with custom_data.

Run: python scripts/fix_fts.py
"""
import sqlite3
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

    cur.execute("SELECT COUNT(*) FROM custom_data")
    before_cd = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM custom_data_fts")
    before_fts = cur.fetchone()[0]
    log.info("Before: custom_data=%d, custom_data_fts=%d (delta=%d)",
             before_cd, before_fts, before_fts - before_cd)

    if before_cd == before_fts:
        log.info("FTS already in sync — nothing to do.")
        conn.close()
        return

    # FTS5 (non-content table): orphan rows have rowids not present in custom_data.
    # We cannot SELECT directly from FTS5 by rowid, so we get all valid IDs from
    # custom_data and delete FTS rows whose rowid is not among them via a shadow-table
    # approach: rebuild by deleting all FTS rows then re-inserting from custom_data.
    log.info("FTS5 non-content table with %d orphan rows — rebuilding from custom_data...",
             before_fts - before_cd)

    # Step 1: Delete all FTS rows
    cur.execute("DELETE FROM custom_data_fts")
    conn.commit()
    log.info("Cleared FTS table.")

    # Step 2: Re-insert all rows from custom_data
    cur.execute("SELECT id, category, key, value FROM custom_data")
    rows = cur.fetchall()
    cur.executemany(
        "INSERT INTO custom_data_fts (rowid, category, key, value_text) VALUES (?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    log.info("Re-inserted %d rows into FTS.", len(rows))

    # Step 3: Optimize
    conn.execute("INSERT INTO custom_data_fts(custom_data_fts) VALUES('optimize')")
    conn.commit()
    log.info("FTS optimize complete.")

    # Verify
    cur.execute("SELECT COUNT(*) FROM custom_data_fts")
    after_fts = cur.fetchone()[0]
    log.info("After:  custom_data=%d, custom_data_fts=%d (delta=%d)",
             before_cd, after_fts, after_fts - before_cd)

    if before_cd == after_fts:
        log.info("FTS sync verified OK.")
    else:
        log.warning("FTS still out of sync — delta=%d, investigate.", after_fts - before_cd)

    # Run integrity check
    try:
        conn.execute("INSERT INTO custom_data_fts(custom_data_fts) VALUES('integrity-check')")
        log.info("FTS integrity-check passed.")
    except Exception as e:
        log.error("FTS integrity-check FAILED: %s", e)

    conn.close()


if __name__ == "__main__":
    main()
