# Ivalua AI Assistant — ConPort Knowledge Base

Persistent, AI-queryable memory for the complete Ivalua platform:
**~1,800 database tables** (59 modules, fully indexed with bidirectional
FK relationships) + **documentation** sourced from both the `entries/`
JSON workflow (small curated docs) and the `Documentation/` folder
(bulk PDF/DOCX/PPTX import). All data lives in a single SQLite-backed
ConPort MCP server that any AI model (Windsurf, Cursor, Claude Desktop,
VS Code with MCP) can query without reading source files and without
hallucinating table/column names.

**Fully portable.** No Python, no admin rights, no PATH edits, no package
manager, no hardcoded paths. Clone, configure your editor once, done.

---

## 1. Installation

> **Prerequisites:** `git` installed, and an internet connection on the
> **first** launch only. That's it. No Python, no admin rights, no
> installers, no PATH edits.

### 1a. Clone the repo

```bash
git clone https://github.com/Abdelakil/Ivalua-AI-Assistant.git
cd Ivalua-AI-Assistant
```

The SQLite knowledge base (`context_portal/context.db`, ~46 MB) is
committed to the repo, so the clone is immediately usable — no
separate download step.

### 1b. Make the launcher executable (macOS / Linux only)

If you used `git clone` (step 1a), the executable bit is preserved
in the git index — you can skip to 1c.

If you instead **downloaded the ZIP** from the GitHub "Code → Download
ZIP" button, GitHub strips all Unix file modes. You **must** run:

```bash
chmod +x conport_launcher.sh
chmod +x scripts/bootstrap.sh
chmod +x .githooks/pre-commit     # only if you plan to use the pre-commit hook
```

Skipping this causes the exact error Windsurf reports as:

```
failed to start command: fork/exec .../conport_launcher.sh: permission denied
```

On Windows the `.cmd` file doesn't need this.

### 1c. Pre-warm the toolchain (**strongly recommended on first install**)

The very first launch downloads `uv` (~20 MB), a portable Python
(~30 MB), and installs ~130 packages (`context-portal-mcp`, its
deps, etc.). On a fresh machine this takes **2–5 minutes** — longer
than the **60-second MCP timeout** that Windsurf/VS Code/Cursor
enforce, which will surface as:

```
MCP Server Error: MCP server timed out after 60 seconds.
```

To avoid this, run the bootstrap **once** from a terminal before
hooking up your editor:

```bash
# macOS / Linux  (if you got "Permission denied", run the chmod in 1b first)
./scripts/bootstrap.sh
```

```powershell
# Windows
scripts\bootstrap.cmd
```

The script downloads everything, builds the local `.venv`, and
smoke-tests the ConPort server — then exits. Your editor's
subsequent MCP connection will start in **< 3 seconds**, well
under any client timeout.

> Already hit the timeout? You have two options: (a) run the
> bootstrap above and restart your editor, or (b) keep clicking
> "Retry" in the editor — the download continues in the background
> and eventually succeeds.

### 1d. Run the tool — pick **one** of the following

You almost never run the launcher by hand. Instead, point your AI
editor at it and the editor runs it for you as an MCP server.

---

#### Option 1 — VS Code (easiest, zero editing)

The repo already ships `.vscode/mcp.json` with a workspace-relative
path. Nothing to create.

1. Open the cloned folder in VS Code:
   ```bash
   code .
   ```
2. Reload the window: `Ctrl+Shift+P` → **Developer: Reload Window**.
3. Open the Command Palette → **MCP: List Servers** → you should see
   `conport` listed and in state **Running** (or **Starting…** on the
   first run — see section 1d).
4. Ask Copilot Chat / any MCP-aware chat panel:
   > "Using the conport MCP server, list the tables in the supplier module."

Requires **VS Code ≥ 1.95** (built-in MCP) or the **MCP** extension
for older builds.

---

#### Option 2 — Windsurf

Edit your Windsurf MCP config file:

- **Windows:** `%USERPROFILE%\.codeium\windsurf\mcp_config.json`
- **macOS / Linux:** `~/.codeium/windsurf/mcp_config.json`

Add the `conport` entry (replace the path with wherever you cloned
the repo):

**Windows**
```json
{
  "mcpServers": {
    "conport": {
      "command": "C:\\Users\\YOU\\path\\to\\Ivalua-AI-Assistant\\conport_launcher.cmd",
      "disabled": false
    }
  }
}
```

**macOS / Linux**
```json
{
  "mcpServers": {
    "conport": {
      "command": "/Users/you/path/to/Ivalua-AI-Assistant/conport_launcher.sh",
      "disabled": false
    }
  }
}
```

Save, **fully restart Windsurf**, then open the MCP panel to confirm
`conport` is running.

> The Windsurf config lives *outside* the repo, so you must use an
> **absolute** path. The VS Code config lives *inside* the repo and
> uses `${workspaceFolder}`, which is why Option 1 needs no editing.

---

#### Option 3 — Cursor / Claude Desktop / any other MCP client

Point the client at the launcher with an absolute path. The config
shape is the same as Windsurf (see Option 2) — the exact file
location varies per product:

- **Cursor:** Settings → MCP → Add new server → Command:
  `C:\…\conport_launcher.cmd` (or `.sh`).
- **Claude Desktop:** `%APPDATA%\Claude\claude_desktop_config.json`
  (Windows) or `~/Library/Application Support/Claude/claude_desktop_config.json`
  (macOS), same JSON shape as Windsurf.

Restart the client afterwards.

---

#### Option 4 — Manual / headless (for debugging)

You *can* run the launcher directly from a terminal. It speaks the
MCP protocol over stdio, so you'll see JSON-RPC, not a friendly UI —
this is only useful to confirm the bootstrap succeeds.

```powershell
# Windows PowerShell
.\conport_launcher.cmd
```

```bash
# macOS / Linux
./conport_launcher.sh
```

Press `Ctrl+C` to stop. To quit cleanly from the JSON-RPC side, send
`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}` followed
by EOF.

### 1e. Install the ConPort custom instructions (**required**)

Running the MCP server is only half the setup. The LLM itself also
needs to know **when** and **how** to call ConPort tools — otherwise
it'll just ignore them. Upstream ConPort
([GreatScottyMac/context-portal](https://github.com/GreatScottyMac/context-portal))
ships a set of strategy files for this, and this repo bundles copies
in `conport-custom-instructions/`:

| File                                   | Use with                         |
|----------------------------------------|----------------------------------|
| `cascade_conport_strategy.md`          | **Windsurf Cascade**             |
| `generic_conport_strategy.md`          | Any MCP-capable LLM (fallback)   |
| `cline_conport_strategy.md`            | Cline (VS Code extension)        |
| `roo_code_conport_strategy.md`         | Roo Code (VS Code extension)     |

Install the one that matches your editor:

#### Windsurf (Cascade)

1. Windsurf menu → **Settings** → **Customizations** → **Global Rules**
   (or **Workspace Rules** for this repo only).
2. Paste the **full contents** of
   `conport-custom-instructions/cascade_conport_strategy.md`.
3. Save.
4. **At the start of every new Cascade session**, send the magic phrase:

   > **Initialize according to custom instructions**

   This triggers the initialization sequence defined in the strategy
   (probes `context_portal/context.db`, loads product/active context,
   recent decisions, etc.). **Without this phrase Cascade will not
   auto-load ConPort memory.**

#### VS Code (Cline / Roo Code / Copilot Chat)

- **Cline:** Settings → **Custom Instructions** → paste contents of
  `cline_conport_strategy.md`.
- **Roo Code:** Settings → **Custom Instructions** → paste contents of
  `roo_code_conport_strategy.md`.
- **Copilot Chat / other:** create `.github/copilot-instructions.md`
  (or the extension's equivalent) and paste contents of
  `generic_conport_strategy.md`.

#### Cursor / Claude Desktop / other

Paste `generic_conport_strategy.md` into the product's
system-prompt / custom-instructions field. The generic strategy
uses `get_conport_schema` to discover tool names at runtime, so it
works on any MCP-capable LLM.

> **Keeping strategies up to date** — this is automated:
>
> - **Weekly** a scheduled GitHub Action
>   (`.github/workflows/sync-custom-instructions.yml`) fetches the
>   latest strategy files from upstream and, if anything changed,
>   opens a pull request for review.
> - **On demand** — go to GitHub → Actions →
>   **Sync upstream custom instructions** → *Run workflow*.
> - **Locally** — `python scripts/sync_custom_instructions.py`
>   (use `--check` for a dry run, or `--ref v1.2.3` to pin).
>
> A PR is opened rather than a direct push so a human can review
> the diff — upstream strategy changes affect how the LLM behaves.

### 1f. Verify it works

1. Start a **new session** with your AI.
2. Send: **"Initialize according to custom instructions"** (Windsurf)
   — other editors auto-apply their custom instructions.
3. Ask:
   > "Using the conport MCP server, what are the tables in the supplier module?"

If the answer contains real table names like `t_sup_supplier`,
`t_sup_internal_team`, `t_sup_naf` (rather than plausibly-guessed
names), the pipeline is live end-to-end.

---

## 2. Keeping your knowledge base up to date

The knowledge base receives content from **two** sources:

| Source | Workflow | What triggers a DB update |
|---|---|---|
| `entries/*.json` | JSON entries (schema / docs / tips) | Push to `main` → CI validates, imports, commits DB |
| `Documentation/` | Bulk documentation (PDF/DOCX/PPTX/TXT) | Run `import_documentation.py` locally, then commit DB |

### Pull the latest DB

After any push to `main` that changed the database, pull to stay current:

### 2a. Pull the latest DB

```bash
cd /path/to/Ivalua-AI-Assistant
git pull --ff-only
```

That's it. The next MCP call sees the new content immediately — no
restart of the editor required (ConPort reads from SQLite on every
query).

> **If you only use the repo as an AI knowledge base** (no local
> commits), `git pull --ff-only` always succeeds. If you've made
> local changes to `context.db` (rare — don't do this), the pull
> will conflict and you should `git reset --hard origin/main` to
> discard your local edits and accept the CI-built DB.

### 2b. Automate the pull (optional)

If you want the DB to refresh without thinking about it, add a
scheduler job:

**Windows (Task Scheduler, every hour)**
```powershell
schtasks /Create /SC HOURLY /TN "IvaluaKB-Sync" /TR `
  "powershell -NoProfile -Command `"cd 'C:\path\to\Ivalua-AI-Assistant'; git pull --ff-only`""
```

**macOS / Linux (cron, every hour)**
```bash
( crontab -l 2>/dev/null; echo "0 * * * * cd ~/Ivalua-AI-Assistant && git pull --ff-only >/dev/null 2>&1" ) | crontab -
```

### 2c. Force-refresh after a big batch import

If someone just pushed a large update and you want it *now*:

```bash
git fetch origin
git reset --hard origin/main
```

This discards any local changes (including the CI-rebuilt `.venv`
cache if you've touched it) and snaps you to the exact state on
GitHub.

### 2d. Want the latest custom-instruction strategies too?

The same `git pull` pulls in any merged PR from the weekly
`sync-custom-instructions` workflow, so your
`conport-custom-instructions/*.md` files stay current with upstream.
No separate action needed.

---

## 3. Repository layout

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
│   ├── validate-and-import.yml            ← CI: validate → import → commit db
│   └── sync-custom-instructions.yml       ← weekly upstream strategy sync (PR)
├── .githooks/
│   └── pre-commit                         ← local validation before commit
├── scripts/
│   ├── bootstrap.sh / .cmd                ← pre-warm toolchain (run once)
│   ├── validate_entries.py                ← JSON validator (stdlib only)
│   ├── install_hooks.py                   ← one-shot hook installer
│   └── sync_custom_instructions.py        ← pull upstream strategies
├── conport-custom-instructions/           ← paste these into your editor's rules
│   ├── cascade_conport_strategy.md        ← Windsurf Cascade
│   ├── generic_conport_strategy.md        ← any MCP-capable LLM
│   ├── cline_conport_strategy.md          ← Cline (VS Code)
│   └── roo_code_conport_strategy.md       ← Roo Code (VS Code)
├── entries/                               ← ← ← USER CONTRIBUTIONS GO HERE
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
        ├── import_documentation.py        ← Documentation/ → incremental import
        ├── rebuild_embeddings.py          ← manual vector store rebuild
        └── module_toggle.py               ← enable/disable modules at runtime
```

Auto-created on first run (never commit these — already in `.gitignore`):

```
.tools/    .venv/    context_portal/import_data/*.json
context_portal/conport_vector_data/    context_portal/logs/
```

`context_portal/import_data/doc_manifest.json` is tracked — it stores the
incremental import state for the `Documentation/` bulk importer.

---

## 4. Contributing content (the `entries/` workflow)

All user contributions live under `entries/` as JSON files. **Do not
edit `context.db` directly** — CI rebuilds it on every push to `main`.

### 4.1 Pick the right subfolder

| Subfolder       | ConPort category        | Use for                                    |
|-----------------|-------------------------|--------------------------------------------|
| `entries/schema/` | `Database_Schema`        | Table definitions, columns, FK relations    |
| `entries/docs/`   | `IVALUA_Documentation`   | Functional docs, process descriptions       |
| `entries/tips/`   | `Tips`                   | Gotchas, best practices, verified facts     |

### 4.2 Copy the template, fill it in

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

### 4.3 Validate locally (optional but recommended)

```bash
python scripts/validate_entries.py               # all files
python scripts/validate_entries.py entries/tips/my_tip.json
```

Exit code is 0 on success, 1 on validation errors, 2 on I/O errors.
**CI runs the exact same validator.**

### 4.4 Install the pre-commit hook (one-time)

Blocks commits that contain invalid JSON:

```bash
python scripts/install_hooks.py           # install
python scripts/install_hooks.py --uninstall
git commit --no-verify                    # bypass once
```

### 4.5 Commit & push

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

## 5. Bulk documentation import (the `Documentation/` workflow)

For large documentation sets (PDF/DOCX/PPTX/TXT files), place files in the
`Documentation/` folder organized by module subdirectories.

### 5.1 Run the incremental importer

```bash
python context_portal/scripts/import_documentation.py
```

This script:
- **Scans** all files in `Documentation/`
- **Compares mtimes** against `doc_manifest.json` — only processes changed/new/deleted files
- **Extracts text** (PDF via PyPDF2, DOCX via python-docx, PPTX via python-pptx)
- **Cleans noise** (copyright lines, page/slide numbers, empty bullets)
- **Chunks** large documents into ~3 KB segments with 500 char overlap
- **Inserts** chunks into `context.db` with metadata (noise_ratio, module, topic, file_path)
- **Rebuilds** module indexes (`DOC_INDEX_*`) automatically
- **Updates** `doc_manifest.json` with new mtimes and generated chunk keys

### 5.2 Commit and push

```bash
git add context_portal/context.db context_portal/import_data/doc_manifest.json
git commit -m "docs: bulk import from Documentation/"
git push
```

### 5.3 Adding new files later

Simply drop new files into `Documentation/` and re-run the importer. Only the
new or modified files are re-processed — the other 1,400+ files are skipped.

---

## 6. ConPort key schemes (memorize these — they are your API)

### 6.1 Database schema

| Purpose                  | Key pattern                     | Example                         |
|--------------------------|---------------------------------|---------------------------------|
| One table                | `TABLE_{MODULE}_{TABLE}`        | `TABLE_BAS_T_BAS_LEGAL_COMPANY` |
| Module → list of tables  | `MODULE_{MODULE}`               | `MODULE_SUP`                    |
| All-modules overview     | `MODULE_INDEX`                  | —                               |

FK relationships are **bidirectional**: `foreign_keys_out` +
`foreign_keys_in` per table — no joins, no extra queries.

### 6.2 Documentation

| Purpose                  | Key pattern                       | Example                        |
|--------------------------|-----------------------------------|--------------------------------|
| One document             | `DOC_{MODULE_SLUG}_{TOPIC_SLUG}`  | `DOC_SUPPLIER_MANAGEMENT_ONBOARDING` |
| Module → list of docs    | `DOC_INDEX_{MODULE_SLUG}`         | `DOC_INDEX_SUPPLIER_MANAGEMENT` |
| All-docs overview        | `DOC_INDEX_ALL`                   | —                              |

### 6.3 Tips

| Purpose | Key pattern         | Example            |
|---------|---------------------|--------------------|
| One tip | `TIP_{TOPIC}`       | `TIP_PK_CONVENTION` |

---

## 7. The safety proxy

`context_portal/scripts/conport_safe_proxy.py` is an MCP stdio proxy
that sits between your editor and the real ConPort server. It:

- Rejects `get_custom_data(category=null, key=null)` (dumps entire DB → IDE crash).
- Auto-rewrites partial-null lookups to the safety README key.
- Hardens tool schemas so LLMs see required params up front.

It's wired in automatically by the launcher. Nothing to configure.

---

## 8. Architecture

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

## 9. Local development

### Rebuild the DB from scratch from entries/

```bash
python context_portal/scripts/import_all_entries.py
python context_portal/scripts/import_to_conport.py 'schema_chunk_*.json'
python context_portal/scripts/import_to_conport.py 'doc_chunk_*.json'
python context_portal/scripts/import_to_conport.py 'tips_chunk_*.json'
```

### Rebuild vector embeddings (manual)

If semantic search returns stale results after a bulk import, rebuild all
embeddings from the current DB rows:

```bash
python context_portal/scripts/rebuild_embeddings.py
```

This clears the ChromaDB collection and regenerates vectors for every
custom_data row. The MCP server also auto-rebuilds on its first semantic
search after a restart.

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

## 10. Troubleshooting

| Symptom                                                 | Fix                                                           |
|---------------------------------------------------------|---------------------------------------------------------------|
| `MCP server timed out after 60 seconds.`                | Run `./scripts/bootstrap.sh` (Linux/macOS) or `scripts\bootstrap.cmd` (Windows) once from a terminal, then restart the editor. See §1c. |
| `permission denied … conport_launcher.sh`               | You downloaded the ZIP. Run `chmod +x conport_launcher.sh scripts/bootstrap.sh`. See §1b. |
| "File not found" on the launcher path                   | VS Code: path in `.vscode/mcp.json` is workspace-relative, ensure you opened the repo root. Windsurf: must be absolute. |
| macOS: "uv can't be opened, developer unverified"       | `xattr -d com.apple.quarantine .tools/uv`                      |
| `git pull` refuses with conflict on `context.db`        | `git reset --hard origin/main` — you accidentally modified the DB locally. See §2a. |
| CI fails on validation                                  | Run `python scripts/validate_entries.py` locally — same errors. |
| Hook not running                                        | Run `python scripts/install_hooks.py` (once per clone).        |
| Want to force a full re-import (entries)                | GitHub → Actions → **Validate & Import Entries** → Run workflow. |
| Want to force a full re-import (documentation)          | GitHub → Actions → **Import Documentation** → Run workflow.      |

---

## 11. FAQ

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

## 12. License

Internal knowledge base. See repository settings for licensing details.
