"""Unified Entry Importer for ConPort.

Scans entries/ folder for JSON files, detects type from filename prefix,
and processes accordingly:
- schema_*.json → Database_Schema
- doc_*.json → IVALUA_Documentation
- tip_*.json → Tips

This is the single import script for the collaborative workflow.
"""
import json
import re
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(__file__).resolve().parents[2]
ENTRIES_DIR = WORKSPACE / "entries"
OUTPUT_DIR = WORKSPACE / "context_portal" / "import_data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CHUNK_SIZE = 50  # items per output chunk file


def slugify(s: str) -> str:
    """Convert to uppercase with underscores for ConPort keys."""
    s = s.upper()
    s = re.sub(r"[^A-Z0-9]+", "_", s)
    return s.strip("_")


def detect_entry_type(filename: str):
    """Detect entry type from filename prefix."""
    if filename.startswith("schema_"):
        return "schema"
    elif filename.startswith("doc_"):
        return "documentation"
    elif filename.startswith("tip_"):
        return "tip"
    return None


def load_all_entries():
    """Load all JSON files from entries/ subdirectories (schema/, docs/, tips/)."""
    entries = []
    if not ENTRIES_DIR.exists():
        print(f"Entries directory not found: {ENTRIES_DIR}")
        return entries
    
    # Map subdirectories to entry types
    subdirs = {
        "schema": "schema",
        "docs": "documentation",
        "tips": "tip"
    }
    
    for subdir_name, entry_type in subdirs.items():
        subdir_path = ENTRIES_DIR / subdir_name
        if not subdir_path.exists():
            print(f"  Warning: {subdir_name}/ directory not found, skipping")
            continue
        
        for fp in sorted(subdir_path.glob("*.json")):
            # Skip templates and example files
            if fp.name == "template.json" or fp.name == "example.json" or fp.name.startswith("."):
                continue
            
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    entry_data = json.load(f)
                    entries.append({
                        "type": entry_type,
                        "filename": f"{subdir_name}/{fp.name}",
                        "data": entry_data
                    })
                    print(f"  Loaded: {subdir_name}/{fp.name} ({entry_type})")
            except Exception as e:
                print(f"  Error loading {subdir_name}/{fp.name}: {e}")
    
    return entries


def process_schema_entry(entry):
    """Convert schema entry to ConPort format."""
    data = entry["data"]
    
    # Validate required fields
    if "module" not in data or "table_technical_name" not in data:
        print(f"  Warning: Skipping schema entry without module or table_technical_name")
        return None
    
    module = data["module"]
    table = data["table_technical_name"]
    key = f"TABLE_{module}_{table}".upper()
    
    return {
        "category": "Database_Schema",
        "key": key,
        "value": data
    }


def process_documentation_entry(entry):
    """Convert documentation entry to ConPort format."""
    data = entry["data"]
    
    # Validate required fields
    if "module" not in data or "topic" not in data:
        print(f"  Warning: Skipping documentation entry without module or topic")
        return None
    
    module = data["module"]
    topic = data["topic"]
    
    # Generate key
    module_slug = slugify(module)
    topic_slug = slugify(topic)
    key = f"DOC_{module_slug}_{topic_slug}"[:250]
    
    # Build value with additional metadata
    value = {
        "module": module,
        "topic": topic,
        "file_path": data.get("file_path", ""),
        "content_type": data.get("content_type", "json"),
        "summary": data.get("summary", ""),
        "key_concepts": data.get("key_concepts", []),
        "content": data.get("content", ""),
        "sections": data.get("sections", []),
        "size_bytes": len(json.dumps(data).encode("utf-8")),
        "char_count": len(data.get("content", "")),
        "truncated": False,
        "is_binary_only": False,
        "versions": [],
        "manual_entry": True,
    }
    
    return {
        "category": "IVALUA_Documentation",
        "key": key,
        "value": value
    }


def process_tip_entry(entry):
    """Convert tip entry to ConPort format."""
    data = entry["data"]
    
    # Validate required fields
    if "tip_id" not in data:
        print(f"  Warning: Skipping tip entry without tip_id")
        return None
    
    tip_id = data["tip_id"]
    # Ensure tip_id follows TIP_ format
    if not tip_id.startswith("TIP_"):
        tip_id = f"TIP_{tip_id}"
    
    return {
        "category": "Tips",
        "key": tip_id.upper(),
        "value": {
            "topic": data.get("topic", ""),
            "summary": data.get("summary", ""),
            "detail": data.get("detail", ""),
            "tags": data.get("tags", []),
            "related_schema_tables": data.get("related_schema_tables", []),
            "related_doc_keys": data.get("related_doc_keys", []),
            "source": data.get("source", "unknown"),
        }
    }


def build_conport_items(entries):
    """Convert all entries to ConPort format."""
    items = []
    schema_items = []
    doc_items = []
    tip_items = []
    module_topics = {}
    
    for entry in entries:
        entry_type = entry["type"]
        
        if entry_type == "schema":
            item = process_schema_entry(entry)
            if item:
                schema_items.append(item)
        
        elif entry_type == "documentation":
            item = process_documentation_entry(entry)
            if item:
                doc_items.append(item)
                # Track for module index
                module = entry["data"]["module"]
                module_slug = slugify(module)
                module_topics.setdefault(module_slug, []).append({
                    "key": item["key"],
                    "topic": entry["data"]["topic"],
                    "file_path": entry["data"].get("file_path", ""),
                    "content_type": entry["data"].get("content_type", "json"),
                    "is_binary_only": False,
                })
        
        elif entry_type == "tip":
            item = process_tip_entry(entry)
            if item:
                tip_items.append(item)
    
    # Add module indexes for documentation
    for module_slug, topics in module_topics.items():
        doc_items.append({
            "category": "IVALUA_Documentation",
            "key": f"DOC_INDEX_{module_slug}",
            "value": {
                "module_slug": module_slug,
                "topic_count": len(topics),
                "topics": sorted(topics, key=lambda x: x["topic"]),
            },
        })
    
    # Add master doc index
    if module_topics:
        doc_items.append({
            "category": "IVALUA_Documentation",
            "key": "DOC_INDEX_ALL",
            "value": {
                "modules": sorted(module_topics.keys()),
                "total_modules": len(module_topics),
                "total_documents": sum(len(v) for v in module_topics.values()),
            },
        })
    
    # Add module indexes for schema
    if schema_items:
        modules = {}
        for item in schema_items:
            m = item["value"]["module"]
            if m not in modules:
                modules[m] = {
                    "module_code": m,
                    "tables": [],
                    "table_count": 0,
                }
            modules[m]["tables"].append({
                "technical_name": item["value"]["table_technical_name"],
                "display_name": item["value"].get("table_display_name", ""),
                "column_count": len(item["value"].get("columns", [])),
            })
        
        for m in modules.values():
            m["table_count"] = len(m["tables"])
            m["tables"].sort(key=lambda x: x["technical_name"])
        
        for m_code, m_data in modules.items():
            schema_items.append({
                "category": "Database_Schema",
                "key": f"MODULE_{m_code}".upper(),
                "value": m_data,
            })
        
        schema_items.append({
            "category": "Database_Schema",
            "key": "MODULE_INDEX",
            "value": {
                "modules": sorted(modules.keys()),
                "total_modules": len(modules),
                "total_tables": sum(m["table_count"] for m in modules.values()),
            },
        })
    
    items = schema_items + doc_items + tip_items
    return items


def write_chunks(items):
    """Write items to chunk JSON files by category."""
    if not items:
        print("No items to write")
        return
    
    # Separate by category
    by_category = {
        "Database_Schema": [],
        "IVALUA_Documentation": [],
        "Tips": []
    }
    
    for item in items:
        cat = item["category"]
        if cat in by_category:
            by_category[cat].append(item)
    
    # Write chunks for each category
    for category, cat_items in by_category.items():
        if not cat_items:
            continue
        
        # Remove existing chunks for this category
        prefix_map = {
            "Database_Schema": "schema_chunk",
            "IVALUA_Documentation": "doc_chunk",
            "Tips": "tips_chunk"
        }
        prefix = prefix_map.get(category, "chunk")
        
        for old in OUTPUT_DIR.glob(f"{prefix}_*.json"):
            old.unlink()
        
        # Write in chunks
        for i in range(0, len(cat_items), CHUNK_SIZE):
            chunk = cat_items[i:i + CHUNK_SIZE]
            if category == "Database_Schema":
                out = OUTPUT_DIR / f"{prefix}_{i // CHUNK_SIZE:03d}.json"
            else:
                out = OUTPUT_DIR / f"{prefix}_{i // CHUNK_SIZE:04d}.json"
            with open(out, "w", encoding="utf-8") as f:
                json.dump(chunk, f, ensure_ascii=False, indent=2)
        
        num_chunks = (len(cat_items) + CHUNK_SIZE - 1) // CHUNK_SIZE
        print(f"  {category}: {len(cat_items)} items in {num_chunks} chunks")
    
    # Write summary
    summary = {
        "total_items": len(items),
        "by_category": {cat: len(items) for cat, items in by_category.items()},
        "generated": datetime.utcnow().isoformat(),
        "source": "unified_import",
    }
    with open(OUTPUT_DIR / "import_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)


def main():
    print(f"Loading entries from {ENTRIES_DIR}...")
    entries = load_all_entries()
    print(f"  Total entries: {len(entries)}")
    
    if not entries:
        print("No entries found. Exiting.")
        return
    
    print("Building ConPort items...")
    items = build_conport_items(entries)
    print(f"  Total items: {len(items)}")
    
    print("Writing chunk files...")
    write_chunks(items)
    
    print("Done.")
    print("\nTo import into ConPort database:")
    print("  python context_portal/scripts/import_to_conport.py schema_chunk_*.json")
    print("  python context_portal/scripts/import_to_conport.py doc_chunk_*.json")
    print("  python context_portal/scripts/import_to_conport.py tips_chunk_*.json")


if __name__ == "__main__":
    main()
