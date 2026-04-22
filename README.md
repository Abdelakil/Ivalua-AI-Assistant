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

```bash
chmod +x conport_launcher.sh
```

On Windows the `.cmd` file doesn't need this.

### 1c. Run the tool — pick **one** of the following

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

### 1d. First-run bootstrap (~50 s, one time only)

The **very first** time the launcher runs (via your editor or
manually), it will:

1. Download a standalone `uv` binary (~20 MB) into `.tools/`.
2. `uv` downloads a portable CPython interpreter (~30 MB) into the
   same folder.
3. `uv sync` builds a project-local `.venv` from `pyproject.toml`
   and installs `context-portal-mcp` + its dependencies.
4. Launches the safety proxy, which spawns the real ConPort server.

Every subsequent launch is **< 3 seconds**.

Everything lives **inside the repo folder** (`.tools/`, `.venv/`).
Delete the repo folder and nothing is left on your system.

> If your editor's MCP client times out during the 50 s bootstrap,
> just retry the same question — the bootstrap continues in the
> background and the next call will succeed instantly.

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
│   ├── validate-and-import.yml            ← CI: validate → import → commit db
│   └── sync-custom-instructions.yml       ← weekly upstream strategy sync (PR)
├── .githooks/
│   └── pre-commit                         ← local validation before commit
├── scripts/
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
