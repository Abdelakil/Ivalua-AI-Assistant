# How to Add Content to the Knowledge Base

There are three types of content and three corresponding workflows. Pick the
one that matches what you want to add.

---

## Quick decision guide

| I want to add… | Use this path |
|---|---|
| A curated documentation entry (written/summarised manually) | [`entries/docs/`](#1-curated-documentation-entry) |
| A verified gotcha, best practice, or quick fact | [`entries/tips/`](#2-tip-entry) |
| A database table definition (columns, FK relations) | [`entries/schema/`](#3-schema-table-entry) |
| A PDF / DOCX / PPTX file | [`Documentation/<module>/`](#4-bulk-pdf--docx--pptx-import) |

All four paths are CI-automated: push to `main` and GitHub Actions rebuilds
the database — no manual import step required.

---

## 1. Curated documentation entry

Best for: process descriptions, functional explanations, how-to guides written
or summarised by hand (not raw PDFs).

### 1.1 Create the file

```bash
cp entries/docs/template.json entries/docs/my_topic.json
```

### 1.2 Fill in the fields

```json
{
  "module": "Supplier Management",
  "topic": "Supplier Onboarding Workflow",
  "summary": "Step-by-step process for onboarding new suppliers.",
  "key_concepts": ["onboarding", "approval workflow", "data validation"],
  "content": "Full text of the documentation goes here.\n\nUse \\n for line breaks.",
  "sections": [
    { "title": "Step 1 — Initial Registration", "content": "..." },
    { "title": "Step 2 — Approval", "content": "..." }
  ]
}
```

| Field | Required | Notes |
|---|---|---|
| `module` | ✅ | Free-form module name, e.g. `"Supplier Management"` |
| `topic` | ✅ | Non-empty, unique within the module |
| `summary` | ➖ | 1–3 sentences |
| `key_concepts` | ➖ | Array of strings — improves search relevance |
| `content` | ➖ | Full text body |
| `sections` | ➖ | Array of `{ "title": "…", "content": "…" }` objects |
| `file_path` | ➖ | Source file reference if applicable |
| `content_type` | ➖ | `"pdf"`, `"docx"`, `"json"` etc. |

### 1.3 Validate locally

```bash
python scripts/validate_entries.py entries/docs/my_topic.json
```

### 1.4 Push

```bash
git add entries/docs/my_topic.json
git commit -m "docs: add supplier onboarding workflow"
git push
```

CI validates, imports, and commits the updated `context.db` automatically.

---

## 2. Tip entry

Best for: verified gotchas, configuration quirks, ETL tricks, SQL caveats —
short actionable facts the AI should recall accurately.

### 2.1 Create the file

```bash
cp entries/tips/template.json entries/tips/my_tip.json
```

### 2.2 Fill in the fields

```json
{
  "tip_id": "TIP_MY_TOPIC_NAME",
  "topic": "Short title",
  "summary": "One-sentence summary the AI will quote directly.",
  "detail": "Full explanation. Include examples, edge cases, version notes.",
  "tags": ["etl", "configuration", "admin"],
  "related_schema_tables": ["t_bas_unit_conversion"],
  "related_doc_keys": ["DOC_PLATFORM_ADMIN_AND_CONFIG_..."],
  "source": "documentation"
}
```

| Field | Required | Notes |
|---|---|---|
| `tip_id` | ✅ | `UPPER_SNAKE_CASE`. `TIP_` prefix is optional (auto-added). |
| `topic` | ✅ | Short human-readable title |
| `summary` | ✅ | One sentence — the AI will surface this in answers |
| `detail` | ✅ | Full explanation, examples, caveats |
| `tags` | ➖ | Array of strings |
| `related_schema_tables` | ➖ | Array of table technical names, e.g. `["t_bas_unit"]` |
| `related_doc_keys` | ➖ | Array of `DOC_*` keys for cross-referencing |
| `source` | ➖ | `"documentation"`, `"experience"`, etc. |

### 2.3 Push

```bash
git add entries/tips/my_tip.json
git commit -m "tip: add TIP_MY_TOPIC_NAME"
git push
```

---

## 3. Schema table entry

Best for: adding or correcting a database table definition (columns, data
types, FK relationships). The schema data powers zero-hallucination SQL generation.

### 3.1 Create the file

```bash
cp entries/schema/template.json entries/schema/t_mymod_my_table.json
```

### 3.2 Fill in the fields

```json
{
  "module": "mymod",
  "table_technical_name": "t_mymod_my_table",
  "table_display_name": "My Table",
  "columns": [
    {
      "column_name": "mytbl_id",
      "display_name": "My Table ID",
      "data_type": "int",
      "max_length": "",
      "allow_null": false,
      "is_primary_key": true,
      "foreign_key": null,
      "domain": "udt_id"
    },
    {
      "column_name": "mytbl_label_en",
      "display_name": "Label (English)",
      "data_type": "nvarchar",
      "max_length": "256",
      "allow_null": true,
      "is_primary_key": false,
      "foreign_key": null,
      "domain": "udt_label"
    }
  ],
  "relationships": {
    "foreign_keys_out": [],
    "foreign_keys_in": []
  }
}
```

| Field | Required | Notes |
|---|---|---|
| `module` | ✅ | Must be one of the recognised module codes (see below) |
| `table_technical_name` | ✅ | Must match `^t_[a-z0-9_]+$` |
| `table_display_name` | ➖ | Human-readable label |
| `columns[]` | ✅ | Non-empty. Each must have `column_name` and `data_type`. |
| `relationships` | ➖ | `foreign_keys_out[]` and `foreign_keys_in[]` arrays |

### 3.3 Valid module codes

```
bas  sup  ctr  req  rsk  inv  spn  ext
cat  src  pur  com  pay  bud  ord
```

**Adding a new module code:** append it to `VALID_SCHEMA_MODULES` in
`scripts/validate_entries.py` before pushing your entry.

### 3.4 Push

```bash
git add entries/schema/t_mymod_my_table.json
git commit -m "schema: add t_mymod_my_table"
git push
```

---

## 4. Bulk PDF / DOCX / PPTX import

Best for: adding a whole document or a set of documents directly from source
files. Text is extracted automatically, cleaned, chunked, and indexed.

### 4.1 Place files under the correct module folder

```
Documentation/
├── 01 - Supplier Management (v176-v178)/
├── 02 - Sourcing/
├── 03 - Contract (v182)/
├── 04 - E-Procurement  (v182)/
├── 05 - Invoicing  (v180-182)/
├── 06 - Spend and BI  (v176-v182)/
├── 3 - Meet the Ivalua Company (v178)/
├── Extranet and PM  (v182)/
├── Platform - Admin and Config  (v178-182)/
├── Platform - Architecture  (v178-182)/
├── Platform - Integrations (v182)/
├── Soft Skills/
├── _Orientation in the Platform/
└── _Refresher Badge (v178-v182)/
```

Supported formats: `.pdf`, `.docx`, `.xlsx`, `.pptx`, `.txt`

### 4.2 Adding a new module folder

If your content doesn't fit an existing folder:

1. **Create the folder** under `Documentation/`:
   ```bash
   mkdir "Documentation/My New Module (v184)"
   ```

2. **Register the slug** in `context_portal/scripts/import_documentation.py`
   by adding an entry to `MODULE_SLUGS` near line 82:
   ```python
   "My New Module (v184)": "MY_NEW_MODULE_V184",
   ```
   The slug must be `UPPER_SNAKE_CASE`. If you skip this step the importer
   still works — it auto-generates a slug from the folder name using
   `slugify()` — but the registered slug gives you a clean predictable key.

3. **Push both** the folder change and the script change together:
   ```bash
   git add "Documentation/My New Module (v184)/my-doc.pdf"
   git add context_portal/scripts/import_documentation.py
   git commit -m "docs: add My New Module with my-doc.pdf"
   git push
   ```

### 4.3 What happens automatically (CI path)

After your push:

1. **`import-documentation.yml`** triggers (watches `Documentation/**`).
2. Extracts text via **PyMuPDF** (primary) → PyPDF2 fallback.
3. Cleans copyright footers, watermarks, page numbers.
4. Detects and skips garbled text (scanned/encrypted PDFs) — logs them to
   `garbled_report.json` artifact.
5. Chunks documents into ~3 KB segments.
6. Inserts into `context.db`, rebuilds FTS index.
7. Commits `context.db` + manifest back to `main`.
8. Do a `git pull` to get the updated DB.

### 4.4 What to do with garbled PDFs

If the importer skips chunks from your PDF (visible in the `garbled_report`
artifact on the Actions run), the PDF is either:
- **Scanned / image-only** — needs OCR first (e.g. Adobe Acrobat, Tesseract).
- **Encryption-restricted** — needs to be unlocked or exported to text.

An OCR'd or unlocked re-export placed in the same path will be picked up on
the next push automatically.

---

## Pre-commit hook (optional but recommended)

Catches JSON errors before they hit CI:

```bash
python scripts/install_hooks.py        # install
python scripts/install_hooks.py --uninstall
git commit --no-verify                 # bypass once
```

---

## Full local import (advanced)

If you want to run the entire pipeline locally without pushing:

```bash
# Curated entries (schema / docs / tips)
uv run python context_portal/scripts/import_all_entries.py
uv run python context_portal/scripts/import_to_conport.py "schema_chunk_*.json"
uv run python context_portal/scripts/import_to_conport.py "doc_chunk_*.json"
uv run python context_portal/scripts/import_to_conport.py "tips_chunk_*.json"

# Bulk documentation
uv run python context_portal/scripts/import_documentation.py

# Rebuild FTS (always do this after a local import)
uv run python scripts/fix_fts.py

# Quality check
uv run python scripts/db_audit.py
```
