"""Post-fix DB quality check. Run: python scripts/db_audit.py"""
import sqlite3
import json
import re
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
DB = WORKSPACE / "context_portal" / "context.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

print("=== Category Counts ===")
cur.execute("SELECT category, COUNT(*) FROM custom_data GROUP BY category ORDER BY COUNT(*) DESC")
for r in cur.fetchall():
    print(f"  {r[0]}: {r[1]}")

print()
print("=== FTS Sync ===")
cur.execute("SELECT COUNT(*) FROM custom_data")
cd = cur.fetchone()[0]
cur.execute("SELECT COUNT(*) FROM custom_data_fts")
fts = cur.fetchone()[0]
print(f"  custom_data={cd}, custom_data_fts={fts}, delta={fts-cd}")

print()
print("=== Copyright leakage (after fix) ===")
cur.execute("SELECT COUNT(*) FROM custom_data WHERE category='IVALUA_Documentation' AND value LIKE '%2023 Ivalua%'")
print(f"  Rows with '2023 Ivalua': {cur.fetchone()[0]}")
cur.execute("SELECT COUNT(*) FROM custom_data WHERE category='IVALUA_Documentation' AND value LIKE '%2024 Ivalua%'")
print(f"  Rows with '2024 Ivalua': {cur.fetchone()[0]}")

print()
print("=== Garbled detection (after fix) ===")
garbled_re = re.compile(r'[A-Za-z] [A-Za-z] [A-Za-z] [A-Za-z]')
cur.execute("SELECT value FROM custom_data WHERE category='IVALUA_Documentation' AND key NOT LIKE 'DOC_INDEX_%'")
garbled = 0
for (v,) in cur.fetchall():
    content = json.loads(v).get("content", "")
    if garbled_re.search(content):
        garbled += 1
print(f"  Spaced-letter garbled chunks: {garbled}")

print()
print("=== Extraction methods ===")
cur.execute("SELECT value FROM custom_data WHERE category='IVALUA_Documentation' AND key NOT LIKE 'DOC_INDEX_%'")
methods = {}
for (v,) in cur.fetchall():
    m = json.loads(v).get("extraction_method", "unknown")
    methods[m] = methods.get(m, 0) + 1
for m, cnt in sorted(methods.items(), key=lambda x: -x[1]):
    print(f"  {m}: {cnt}")

print()
print("=== Quality score distribution ===")
cur.execute("SELECT value FROM custom_data WHERE category='IVALUA_Documentation' AND key NOT LIKE 'DOC_INDEX_%'")
qs = []
for (v,) in cur.fetchall():
    q = json.loads(v).get("quality_score")
    if q is not None:
        qs.append(q)
if qs:
    perfect = sum(1 for q in qs if q == 1.0)
    high = sum(1 for q in qs if 0.8 <= q < 1.0)
    medium = sum(1 for q in qs if 0.5 <= q < 0.8)
    low = sum(1 for q in qs if q < 0.5)
    print(f"  1.0 (perfect): {perfect}  |  0.8-1.0: {high}  |  0.5-0.8: {medium}  |  <0.5: {low}")
    print(f"  Avg quality: {sum(qs)/len(qs):.4f}")
else:
    print("  No quality_score field found (old entries without field)")

print()
print("=== Tips ===")
cur.execute("SELECT key, value FROM custom_data WHERE category='Tips'")
for k, v in cur.fetchall():
    val = json.loads(v)
    print(f"  [{k}] {val.get('topic','')}")

conn.close()
print()
print("Audit complete.")
