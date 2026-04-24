"""Rebuild ChromaDB embeddings for all existing custom_data entries.

This script directly generates embeddings for rows that were inserted
via raw SQLite (bypassing the MCP handlers, which is why the vector
store is currently empty).
"""
import json
import os
import sqlite3
import sys
from pathlib import Path

# Ensure the venv site-packages are on path so we can import context_portal_mcp
venv_site = Path(__file__).resolve().parents[1] / ".venv" / "Lib" / "site-packages"
if str(venv_site) not in sys.path:
    sys.path.insert(0, str(venv_site))

from context_portal_mcp.core import embedding_service
from context_portal_mcp.db import vector_store_service

WORKSPACE = Path(__file__).resolve().parents[1]
DB = WORKSPACE / "context_portal" / "context.db"
WORKSPACE_ID = str(WORKSPACE)

# SentenceTransformer all-MiniLM-L6-v2 has ~256 token limit.
# At ~4 chars/token, truncate to ~2000 chars to stay safe and fast.
MAX_EMBED_CHARS = 2000


def truncate_for_embedding(text: str) -> str:
    if len(text) <= MAX_EMBED_CHARS:
        return text
    # Try to cut at a sentence boundary
    truncated = text[:MAX_EMBED_CHARS]
    last_period = truncated.rfind(".")
    if last_period > MAX_EMBED_CHARS * 0.8:
        return truncated[:last_period + 1]
    return truncated


def main():
    if not DB.exists():
        print(f"Database not found: {DB}")
        sys.exit(1)

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Count total custom_data rows
    cur.execute("SELECT COUNT(*) FROM custom_data")
    total = cur.fetchone()[0]
    print(f"Total custom_data rows: {total}")

    # Ensure vector store path exists
    vector_store_service._get_vector_store_path(WORKSPACE_ID)

    # Fetch all rows
    cur.execute("SELECT id, timestamp, category, key, value FROM custom_data")
    rows = cur.fetchall()
    conn.close()

    success = 0
    skipped = 0
    failed = 0

    for idx, row in enumerate(rows, 1):
        item_id = row["id"]
        category = row["category"]
        key = row["key"]
        value = row["value"]

        # Build text to embed (same format as the MCP handler)
        text_to_embed = f"Category: {category}\nKey: {key}\nValue: {value}"
        text_to_embed = truncate_for_embedding(text_to_embed)

        try:
            vector = embedding_service.get_embedding(text_to_embed.strip())
        except Exception as e:
            print(f"  [{idx}/{total}] EMBED FAIL id={item_id}: {e}")
            failed += 1
            continue

        metadata = {
            "conport_item_id": str(item_id),
            "conport_item_type": "custom_data",
            "category": category,
            "key": key,
            "timestamp_created": row["timestamp"],
        }

        try:
            vector_store_service.upsert_item_embedding(
                workspace_id=WORKSPACE_ID,
                item_type="custom_data",
                item_id=str(item_id),
                vector=vector,
                metadata=metadata,
            )
            success += 1
        except Exception as e:
            print(f"  [{idx}/{total}] UPSERT FAIL id={item_id}: {e}")
            failed += 1
            continue

        if idx % 100 == 0:
            print(f"  [{idx}/{total}] processed (ok={success}, skip={skipped}, fail={failed})")

    print(f"\nDone. Total={total}, Success={success}, Skipped={skipped}, Failed={failed}")

    # Verify
    try:
        collection = vector_store_service.get_or_create_collection(WORKSPACE_ID)
        count = collection.count()
        print(f"Vector store collection count: {count}")
    except Exception as e:
        print(f"Could not verify collection count: {e}")


if __name__ == "__main__":
    main()
