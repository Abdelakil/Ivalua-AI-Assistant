"""Stdio MCP proxy that sanitizes dangerous ConPort calls.

Some agents invoke mcp0_get_custom_data with category=null and key=null,
which dumps the entire custom_data table and crashes the IDE. This
proxy sits between the MCP client (Windsurf) and the real conport-mcp
server, inspects every JSON-RPC request, and rejects dangerous calls
with a helpful error so the agent self-corrects instead of crashing.

Protocol: newline-delimited JSON-RPC 2.0 over stdio (standard MCP stdio
transport). No Content-Length framing.

Launch by pointing your MCP config at this file instead of the real
conport-mcp command. See context_portal/README.md section 10.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from typing import Any

# Real ConPort command. Built dynamically so a bundled `uv` (set via UV_BIN
# env var by the portable launcher) is preferred over the system `uvx`.
def _child_cmd() -> list[str]:
    uv_bin = os.environ.get("UV_BIN")
    if uv_bin and os.path.exists(uv_bin):
        # Bundled uv: `uv run --with context-portal-mcp conport-mcp ...`
        return [
            uv_bin, "run",
            "--with", "context-portal-mcp",
            "conport-mcp",
            "--mode", "stdio",
            "--log-level", "INFO",
        ]
    # Fallback: system-wide uvx (original behavior)
    return [
        "uvx",
        "--from", "context-portal-mcp",
        "conport-mcp",
        "--mode", "stdio",
        "--log-level", "INFO",
    ]

# Tools that require non-null parameters. Map: tool_name -> list of required arg names.
GUARDED_TOOLS: dict[str, list[str]] = {
    "get_custom_data": ["category", "key"],
    "delete_custom_data": ["category", "key"],
}

# Safe fallback when get_custom_data is called with BOTH category and key null.
# Rewriting to a concrete row (instead of returning an error) breaks agent
# retry loops: the agent receives a legitimate tool result containing the
# SAFETY_README, reads the rules, and moves on.
FALLBACK_CATEGORY = "CONPORT_CONTROL"
FALLBACK_KEY = "SAFETY_README"

# Prepended to the rewritten response's text content so the LLM sees a clear
# correction notice inside the tool result (most agents heed in-payload text
# more than error flags).
REWRITE_NOTICE = (
    "!!! PROXY CORRECTION !!!\n"
    "You just called mcp0_get_custom_data with category=null key=null.\n"
    "That is forbidden. The proxy auto-rewrote it to "
    "category='CONPORT_CONTROL', key='SAFETY_README'.\n"
    "READ THE RULES BELOW AND DO NOT REPEAT THE MISTAKE. "
    "For your NEXT call use concrete values, e.g. "
    "category='Database_Schema', key='MODULE_INDEX' to list modules, "
    "or mcp0_search_custom_data_value_fts(category_filter='Database_Schema', "
    "query_term='your search') for fuzzy lookup.\n"
    "--- SAFETY_README PAYLOAD FOLLOWS ---\n\n"
)

ERROR_HINT = (
    "REJECTED by conport_safe_proxy: mcp0_{tool} requires BOTH {params} as "
    "non-null strings. Calling with null/missing values would dump the entire "
    "custom_data table and crash the IDE. "
    "Retry with a concrete category AND key, e.g. "
    "category='CONPORT_CONTROL', key='SAFETY_README' to read the query rules, "
    "or category='Database_Schema', key='MODULE_INDEX' to browse modules, "
    "or category='IVALUA_Documentation', key='DOC_INDEX_ALL' to list doc modules. "
    "For fuzzy search use mcp0_search_custom_data_value_fts with a category_filter."
)


def log(msg: str) -> None:
    """Write diagnostic to stderr so it ends up in the MCP server log."""
    sys.stderr.write(f"[conport_safe_proxy] {msg}\n")
    sys.stderr.flush()


def is_missing(v: Any) -> bool:
    return v is None or (isinstance(v, str) and v.strip() == "")


def classify_tool_call(params: dict) -> tuple[str, str | None]:
    """Classify a tools/call params dict.

    Returns (action, detail) where action is one of:
      - 'pass'    : forward unchanged
      - 'rewrite' : auto-rewrite arguments (detail unused; mutates caller)
      - 'reject'  : block with error message in `detail`
    """
    if not isinstance(params, dict):
        return ("pass", None)
    name = params.get("name")
    if not isinstance(name, str):
        return ("pass", None)
    required = GUARDED_TOOLS.get(name)
    if not required:
        return ("pass", None)
    args = params.get("arguments") or {}
    missing = [p for p in required if is_missing(args.get(p))]
    if not missing:
        return ("pass", None)

    # Special case: get_custom_data with BOTH category AND key missing
    # -> auto-rewrite to a safe concrete query instead of rejecting,
    # so the agent gets a real result and breaks out of retry loops.
    if name == "get_custom_data" and set(missing) >= {"category", "key"}:
        args["category"] = FALLBACK_CATEGORY
        args["key"] = FALLBACK_KEY
        params["arguments"] = args
        return ("rewrite", None)

    # Partial missing or delete_custom_data -> reject (ambiguous, no safe default).
    return (
        "reject",
        ERROR_HINT.format(tool=name, params=" and ".join(f"'{p}'" for p in required)),
    )


# Back-compat alias for tests / external callers.
def validate_tool_call(params: dict) -> str | None:
    action, detail = classify_tool_call(params)
    return detail if action == "reject" else None


def make_error_response(req_id: Any, message: str) -> dict:
    """Return a JSON-RPC tool-call error response the MCP client understands."""
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "content": [{"type": "text", "text": message}],
            "isError": True,
        },
    }


# Hardened schema + description for get_custom_data.
# Injected into tools/list responses so that MCP clients (and the LLM's tool
# picker) see the constraints BEFORE the first call, not only in free-form docs.
HARDENED_GET_CUSTOM_DATA_DESCRIPTION = (
    "Retrieve ONE specific custom_data row by (category, key). "
    "BOTH arguments are REQUIRED and MUST be non-null non-empty strings. "
    "This tool is NOT a list/dump tool - it is a keyed lookup. "
    "Calling it with null/missing category or key is forbidden and will be "
    "auto-rewritten to category='CONPORT_CONTROL', key='SAFETY_README'. "
    "\n\nDiscovery patterns (use these FIRST when you don't know a key):"
    "\n  - category='Database_Schema', key='MODULE_INDEX' -> list of all 59 Ivalua modules"
    "\n  - category='Database_Schema', key='MODULE_{code}' -> tables in one module (e.g. MODULE_SUP)"
    "\n  - category='Database_Schema', key='TABLE_{MOD}_{TABLE}' -> one table's full schema "
    "(e.g. TABLE_SUP_T_SUP_SUPPLIER)"
    "\n  - category='IVALUA_Documentation', key='DOC_INDEX_ALL' -> all doc modules"
    "\n  - category='IVALUA_Documentation', key='DOC_INDEX_{slug}' -> docs in one module"
    "\n  - category='CONPORT_CONTROL', key='SAFETY_README' -> full query rules"
    "\n  - category='CONPORT_CONTROL', key='DISABLED_MODULES' -> currently hidden modules"
    "\n\nFor fuzzy search across many rows, use search_custom_data_value_fts "
    "with a category_filter, NOT this tool."
)


def mutate_tools_list_result(result: dict) -> bool:
    """If result is a tools/list payload, harden the get_custom_data schema.
    Returns True if anything changed."""
    if not isinstance(result, dict):
        return False
    tools = result.get("tools")
    if not isinstance(tools, list):
        return False
    changed = False
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        if tool.get("name") != "get_custom_data":
            continue
        tool["description"] = HARDENED_GET_CUSTOM_DATA_DESCRIPTION
        schema = tool.get("inputSchema") or {}
        if isinstance(schema, dict):
            required = schema.get("required")
            if not isinstance(required, list):
                required = []
            for p in ("category", "key"):
                if p not in required:
                    required.append(p)
            schema["required"] = required
            # Tighten individual property descriptions too.
            props = schema.get("properties")
            if isinstance(props, dict):
                if "category" in props and isinstance(props["category"], dict):
                    props["category"]["description"] = (
                        "REQUIRED non-null non-empty string. Category name "
                        "(e.g. 'Database_Schema', 'IVALUA_Documentation', "
                        "'CONPORT_CONTROL'). Passing null will be auto-rewritten."
                    )
                    # Remove null from type union if present
                    t = props["category"].get("type")
                    if isinstance(t, list) and "null" in t:
                        props["category"]["type"] = [x for x in t if x != "null"] or "string"
                if "key" in props and isinstance(props["key"], dict):
                    props["key"]["description"] = (
                        "REQUIRED non-null non-empty string. Exact key within "
                        "the category (e.g. 'MODULE_INDEX', 'TABLE_SUP_T_SUP_SUPPLIER', "
                        "'SAFETY_README'). Passing null will be auto-rewritten."
                    )
                    t = props["key"].get("type")
                    if isinstance(t, list) and "null" in t:
                        props["key"]["type"] = [x for x in t if x != "null"] or "string"
            tool["inputSchema"] = schema
            changed = True
    return changed


def inject_rewrite_notice(result: dict) -> bool:
    """Prepend REWRITE_NOTICE to the first text content item of a tool-call
    result. Returns True if the result was mutated."""
    if not isinstance(result, dict):
        return False
    content = result.get("content")
    if not isinstance(content, list):
        return False
    for item in content:
        if isinstance(item, dict) and item.get("type") == "text" and "text" in item:
            item["text"] = REWRITE_NOTICE + (item.get("text") or "")
            return True
    return False


def pump_child_to_stdout(
    child: subprocess.Popen,
    lock: threading.Lock,
    rewritten_ids: set,
    rewritten_lock: threading.Lock,
) -> None:
    """Forward every line the child writes to stdout. Uses readline() to avoid
    Python's file-iterator buffering (which would stall pipe-based MCP traffic).

    Additionally:
      - intercepts tools/list responses and hardens the get_custom_data schema
        so the client enforces category+key as required from the very first call.
      - intercepts tool-call responses whose id we auto-rewrote earlier and
        injects a PROXY CORRECTION notice into the payload."""
    assert child.stdout is not None
    while True:
        raw = child.stdout.readline()
        if not raw:
            return  # EOF
        forwarded = raw
        try:
            text = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            if text.strip():
                msg = json.loads(text)
                if isinstance(msg, dict) and "result" in msg:
                    msg_id = msg.get("id")
                    mutated = False
                    # 1) Harden tools/list schema.
                    if mutate_tools_list_result(msg["result"]):
                        log(f"hardened get_custom_data schema in tools/list response id={msg_id}")
                        mutated = True
                    # 2) Inject correction notice into responses for auto-rewritten requests.
                    if msg_id is not None:
                        with rewritten_lock:
                            was_rewritten = msg_id in rewritten_ids
                            if was_rewritten:
                                rewritten_ids.discard(msg_id)
                        if was_rewritten:
                            if inject_rewrite_notice(msg["result"]):
                                log(f"injected correction notice into rewritten response id={msg_id}")
                                mutated = True
                    if mutated:
                        forwarded = (json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8")
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
        with lock:
            sys.stdout.buffer.write(forwarded)
            sys.stdout.buffer.flush()


def main() -> int:
    # Merge environment (pass through everything, plus keep PYTHONUNBUFFERED)
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")

    cmd = _child_cmd()
    log(f"child cmd: {' '.join(cmd)}")
    child = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=sys.stderr,  # child logs go straight to our stderr
        env=env,
        bufsize=0,
    )
    log(f"started child pid={child.pid}")
    assert child.stdin is not None and child.stdout is not None

    out_lock = threading.Lock()
    rewritten_ids: set = set()
    rewritten_lock = threading.Lock()
    t = threading.Thread(
        target=pump_child_to_stdout,
        args=(child, out_lock, rewritten_ids, rewritten_lock),
        daemon=True,
    )
    t.start()

    try:
        while True:
            raw = sys.stdin.buffer.readline()
            if not raw:
                break  # EOF from client
            # Try to parse; if not valid JSON, forward unchanged.
            text = raw.decode("utf-8", errors="replace").rstrip("\r\n")
            if not text.strip():
                child.stdin.write(raw)
                child.stdin.flush()
                continue
            try:
                msg = json.loads(text)
            except json.JSONDecodeError:
                child.stdin.write(raw)
                child.stdin.flush()
                continue

            # Only inspect tools/call requests.
            if (
                isinstance(msg, dict)
                and msg.get("method") == "tools/call"
                and "params" in msg
            ):
                action, detail = classify_tool_call(msg["params"])
                tool = msg["params"].get("name", "?")

                if action == "reject":
                    log(f"blocked {tool} call with missing/null args; id={msg.get('id')}")
                    resp = make_error_response(msg.get("id"), detail or "rejected")
                    line = (json.dumps(resp, ensure_ascii=False) + "\n").encode("utf-8")
                    with out_lock:
                        sys.stdout.buffer.write(line)
                        sys.stdout.buffer.flush()
                    continue  # DO NOT forward the dangerous call

                if action == "rewrite":
                    msg_id = msg.get("id")
                    log(
                        f"rewrote {tool} null/null -> "
                        f"category={FALLBACK_CATEGORY} key={FALLBACK_KEY}; "
                        f"id={msg_id}"
                    )
                    # Remember this id so the response pump injects the
                    # correction notice when the child answers it.
                    if msg_id is not None:
                        with rewritten_lock:
                            rewritten_ids.add(msg_id)
                    # Re-serialize the modified message and forward that instead.
                    rewritten = (
                        json.dumps(msg, ensure_ascii=False) + "\n"
                    ).encode("utf-8")
                    child.stdin.write(rewritten)
                    child.stdin.flush()
                    continue

            # Forward everything else verbatim.
            child.stdin.write(raw)
            child.stdin.flush()
    except (BrokenPipeError, KeyboardInterrupt):
        pass
    finally:
        try:
            child.stdin.close()
        except Exception:
            pass
        child.wait(timeout=5)

    return child.returncode or 0


if __name__ == "__main__":
    sys.exit(main())
