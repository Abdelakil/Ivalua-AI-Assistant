# Ivalua AI Assistant — ConPort Knowledge Base

Persistent, AI-queryable memory for the complete Ivalua platform:
**~1,800 database tables** (59 modules, fully indexed with bidirectional
FK relationships) + **~1,500 documentation files** — all preloaded into
a single SQLite-backed ConPort MCP server that any AI model
(Windsurf, Cursor, Claude Desktop, VS Code with MCP) can query without
reading the source files and without hallucinating table/column names.

**Fully portable.** No Python, no admin rights, no PATH edits, no package
manager, no hardcoded paths. Clone, configure your editor once, done.

---

## 1. Quick start

### 1a. Clone the repo

```bash
git clone https://github.com/Abdelakil/Ivalua-AI-Assistant.git
cd Ivalua-AI-Assistant
```

The SQLite knowledge base (`context_portal/context.db`) ships inside
the repo, so the clone is immediately usable.

### 1b. Configure your editor

#### VS Code (zero-editing, workspace-relative)

The repo ships `.vscode/mcp.json` — nothing to create. Just:

1. Open the cloned folder in VS Code.
2. Reload the window (`Ctrl+Shift+P` → **Developer: Reload Window**).
3. Run **MCP: List Servers** — you should see `conport`.

Requires VS Code ≥ 1.95 (built-in MCP) or the MCP extension.

#### Windsurf / Cursor / Claude Desktop

Add this to your MCP config:

**Windows** — `%USERPROFILE%\.codeium\windsurf\mcp_config.json`
```json
{
  "mcpServers": {
    "conport": {
      "command": "C:\\absolute\\path\\to\\Ivalua-AI-Assistant\\conport_launcher.cmd",
      "disabled": false
    }
  }
}
```

**macOS / Linux** — `~/.codeium/windsurf/mcp_config.json`
```json
{
  "mcpServers": {
    "conport": {
      "command": "/absolute/path/to/Ivalua-AI-Assistant/conport_launcher.sh",
      "disabled": false
    }
  }
}
```

Restart the editor.

### 1c. First-run bootstrap (~50 s, one time only)

On the first MCP invocation, the launcher:

1. Downloads a standalone `uv` binary (~20 MB) into `.tools/`.
2. `uv` downloads a portable CPython (~30 MB) into the same folder.
3. `uv sync` builds a project-local `.venv` from `pyproject.toml`.
4. Launches the safety proxy → real ConPort server.

Every subsequent launch is **< 3 seconds**.

Everything lives **inside the repo folder**. Delete the folder and
nothing is left on the system.

### 1d. Verify it works

Ask your AI:

> "What are the tables in the supplier module?"

If it answers with real table names like `t_sup_supplier`,
`t_sup_internal_team`, `t_sup_naf`, etc. — the pipeline is live.

---

## 2. Repository layout

```
Ivalua-AI-Assistant/
├── README.md                              ← this file (the only doc)
├── conport_launcher.cmd / .sh             ← portable bootstrap entry points
├── pyproject.toml                         ← uv-managed dependency manifest
├── .gitignore
├── .vscode/
│   ├── mcp.json                           ← VS Code MCP config (workspace-relative)
│   ├── settings.json                      ← Python interpreter + formatting
│   └── extensions.json                    ← recommended extensions
├── .github/workflows/
│   └── validate-and-import.yml            ← CI: validate → import → commit db
├── .githooks/
│   └── pre-commit                         ← local validation before commit
├── scripts/
│   ├── validate_entries.py                ← JSON validator (stdlib only)
│   └── install_hooks.py                   ← one-shot hook installer
├── entries/                               ← ← ← USER CONTRIBUTIONS GO HERE
│   ├── README.md
│   ├── schema/  {template,example}.json
│   ├── docs/    {template,example}.json
│   └── tips/    {template,example}.json
└── context_portal/
    ├── context.db                         ← SQLite knowledge base (committed)
    ├── alembic.ini + alembic/             ← schema migrations
    └── scripts/
        ├── conport_safe_proxy.py          ← crash-prevention MCP proxy
        ├── import_all_entries.py          ← entries/ → import chunks
        ├── import_to_conport.py           ← chunks → context.db
        └── module_toggle.py               ← enable/disable modules at runtime
```

Auto-created on first run (never commit these — already in `.gitignore`):

```
.tools/    .venv/    context_portal/import_data/*.json
context_portal/conport_vector_data/    context_portal/logs/
```

---

## 3. Contributing content (the `entries/` workflow)

All user contributions live under `entries/` as JSON files. **Do not
edit `context.db` directly** — CI rebuilds it on every push to `main`.

### 3.1 Pick the right subfolder

| Subfolder       | ConPort category        | Use for                                    |
|-----------------|-------------------------|--------------------------------------------|
| `entries/schema/` | `Database_Schema`        | Table definitions, columns, FK relations    |
| `entries/docs/`   | `IVALUA_Documentation`   | Functional docs, process descriptions       |
| `entries/tips/`   | `Tips`                   | Gotchas, best practices, verified facts     |

### 3.2 Copy the template, fill it in

```bash
cp entries/schema/template.json entries/schema/my_table.json
# edit my_table.json
```

**Schema** (`entries/schema/*.json`) — see `entries/schema/example.json`.

| Field                    | Required | Notes                                                    |
|--------------------------|----------|----------------------------------------------------------|
| `module`                 | ✅        | One of `bas`, `sup`, `ctr`, `req`, `rsk`, `inv`, `spn`, `ext`, `cat`, `src`, `pur`, `com`, `pay`, `bud`, `ord` |
| `table_technical_name`   | ✅        | Must match `^t_[a-z0-9_]+$`                              |
| `table_display_name`     | ➖        | Human-readable label                                     |
| `columns[]`              | ✅        | Non-empty. Each: `column_name`, `data_type`, optional FK |
| `relationships`          | ➖        | `foreign_keys_out[]`, `foreign_keys_in[]`                |

**Docs** (`entries/docs/*.json`) — see `entries/docs/example.json`.

| Field             | Required | Notes                                        |
|-------------------|----------|----------------------------------------------|
| `module`          | ✅        | Full module name, e.g. "Supplier Management" |
| `topic`           | ✅        | Non-empty                                    |
| `content`         | ➖        | Full text                                    |
| `summary`, `key_concepts`, `sections`, `file_path`, `content_type` | ➖ | optional metadata |

**Tips** (`entries/tips/*.json`) — see `entries/tips/example.json`.

| Field      | Required | Notes                                            |
|------------|----------|--------------------------------------------------|
| `tip_id`   | ✅        | `UPPER_SNAKE_CASE`. `TIP_` prefix auto-added    |
| `topic`    | ✅        | Short title                                     |
| `summary`  | ✅        | One sentence                                    |
| `detail`   | ✅        | Full explanation                                |
| `tags[]`, `related_schema_tables[]`, `related_doc_keys[]`, `source` | ➖ | optional |

### 3.3 Validate locally (optional but recommended)

```bash
python scripts/validate_entries.py               # all files
python scripts/validate_entries.py entries/tips/my_tip.json
```

Exit code is 0 on success, 1 on validation errors, 2 on I/O errors.
**CI runs the exact same validator.**

### 3.4 Install the pre-commit hook (one-time)

Blocks commits that contain invalid JSON:

```bash
python scripts/install_hooks.py           # install
python scripts/install_hooks.py --uninstall
git commit --no-verify                    # bypass once
```

### 3.5 Commit & push

```bash
git add entries/schema/my_table.json
git commit -m "schema: add t_bas_my_table"
git push
```

CI will:

1. **Validate** all entries — fails the run if any are invalid.
2. **Import** into `context.db` via `import_all_entries.py`
   → `import_to_conport.py`.
3. **Commit** the updated `context.db` back to `main` with
   `[skip ci]` to avoid loops.
4. **Upload** `context.db` as a workflow artifact (14-day retention).

---

## 4. ConPort key schemes (memorize these — they are your API)

### 4.1 Database schema

| Purpose                  | Key pattern                     | Example                         |
|--------------------------|---------------------------------|---------------------------------|
| One table                | `TABLE_{MODULE}_{TABLE}`        | `TABLE_BAS_T_BAS_LEGAL_COMPANY` |
| Module → list of tables  | `MODULE_{MODULE}`               | `MODULE_SUP`                    |
| All-modules overview     | `MODULE_INDEX`                  | —                               |

FK relationships are **bidirectional**: `foreign_keys_out` +
`foreign_keys_in` per table — no joins, no extra queries.

### 4.2 Documentation

| Purpose                  | Key pattern                       | Example                        |
|--------------------------|-----------------------------------|--------------------------------|
| One document             | `DOC_{MODULE_SLUG}_{TOPIC_SLUG}`  | `DOC_SUPPLIER_MANAGEMENT_ONBOARDING` |
| Module → list of docs    | `DOC_INDEX_{MODULE_SLUG}`         | `DOC_INDEX_SUPPLIER_MANAGEMENT` |
| All-docs overview        | `DOC_INDEX_ALL`                   | —                              |

### 4.3 Tips

| Purpose | Key pattern         | Example            |
|---------|---------------------|--------------------|
| One tip | `TIP_{TOPIC}`       | `TIP_PK_CONVENTION` |

---

## 5. The safety proxy

`context_portal/scripts/conport_safe_proxy.py` is an MCP stdio proxy
that sits between your editor and the real ConPort server. It:

- Rejects `get_custom_data(category=null, key=null)` (dumps entire DB → IDE crash).
- Auto-rewrites partial-null lookups to the safety README key.
- Hardens tool schemas so LLMs see required params up front.

It's wired in automatically by the launcher. Nothing to configure.

---

## 6. Architecture

```
 Your editor (VS Code / Windsurf / Cursor / Claude Desktop)
      │
      ▼
 conport_launcher.cmd | .sh         ← you configured this once
      │  (first run: bootstraps uv + Python + .venv inside repo)
      ▼
 conport_safe_proxy.py              ← blocks destructive calls
      │
      ▼
 conport-mcp  (spawned via uv)      ← the real ConPort server
      │
      ▼
 context_portal/context.db          ← 3,400+ row SQLite knowledge base
```

---

## 7. Local development

### Rebuild the DB from scratch from entries/

```bash
python context_portal/scripts/import_all_entries.py
python context_portal/scripts/import_to_conport.py 'schema_chunk_*.json'
python context_portal/scripts/import_to_conport.py 'doc_chunk_*.json'
python context_portal/scripts/import_to_conport.py 'tips_chunk_*.json'
```

### Reset the auto-downloaded toolchain

```powershell
# Windows
Remove-Item .tools, .venv -Recurse -Force
```

```bash
# macOS / Linux
rm -rf .tools .venv
```

Next launch re-downloads and reinstalls everything.

---

## 8. Troubleshooting

| Symptom                                                 | Fix                                                           |
|---------------------------------------------------------|---------------------------------------------------------------|
| MCP server fails to start on first launch               | Retry. Bootstrap (~50 s) may outlast the editor's MCP timeout. Second try always works. |
| "File not found" on the launcher path                   | VS Code: path in `.vscode/mcp.json` is workspace-relative, ensure you opened the repo root. Windsurf: must be absolute. |
| macOS: "uv can't be opened, developer unverified"       | `xattr -d com.apple.quarantine .tools/uv`                      |
| Linux: permission denied on launcher                    | `chmod +x conport_launcher.sh .tools/uv`                       |
| CI fails on validation                                  | Run `python scripts/validate_entries.py` locally — same errors. |
| Hook not running                                        | Run `python scripts/install_hooks.py` (once per clone).        |
| Want to force a full re-import                          | GitHub → Actions → **Validate & Import Entries** → Run workflow. |

---

## 9. FAQ

**Does committing `context.db` (~46 MB) bloat the repo?**
Each CI run adds one binary diff. For a small team this stays under a
few hundred MB for years. If it ever becomes a problem, run
`git gc --aggressive` or migrate to Git LFS.

**Why not regenerate the DB from scratch on first launch?**
The current DB contains ~3,400 baseline entries whose JSON source
isn't in the repo (they were imported from external data models and
docs). Committing the DB is the simplest way to keep clones
plug-and-play while the `entries/` folder handles incremental growth.

**Can I use a different Python than the bundled one?**
Yes — set `UV_PYTHON=/path/to/python` before launching. But the
bundled one is the tested reference; prefer it.

**How do I add a brand-new module code?**
Append it to `VALID_SCHEMA_MODULES` in
`scripts/validate_entries.py`, then push a schema entry with that code.

---

## 10. License

Internal knowledge base. See repository settings for licensing details.
