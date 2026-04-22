---
description: Query Tips category only (verified gotchas and quick facts)
---

# /tips - Tips Query

Use this command when you need quick verified facts, gotchas, syntax traps, or platform-specific quirks from the Tips category.

## Instructions

**Scope Restriction:**
- ONLY use the `Tips` category in ConPort searches
- NEVER include `Database_Schema` or `IVALUA_Documentation` in searches
- Tips are for quick verified discoveries, not comprehensive documentation
- Always verify tips against your specific Ivalua version and context

## Search Patterns

1. **All tips overview**:
   - Use: `mcp0_get_custom_data(category='Tips', key='TIPS_INDEX')`

2. **FTS tips search**:
   - Use: `mcp0_search_custom_data_value_fts(query_term='...', category_filter='Tips')`
   - Best for finding tips by keyword (e.g., 'smart copy', 'transformation', 'callback')

3. **Semantic tips search**:
   - Use: `mcp0_semantic_search_conport(filter_item_types=['custom_data'], filter_custom_data_categories=['Tips'])`
   - Good for discovering related tips by concept

4. **Specific tip by key**:
   - Use: `mcp0_get_custom_data(category='Tips', key='{TIP_KEY}')`
   - Example: `ETL_SMART_COPY_CASE_WHEN`

## Use Cases
- Quick syntax discoveries (e.g., CASE WHEN in Smart copy method parameters)
- Platform-specific quirks and workarounds
- Verified parameter usage patterns
- Non-obvious configuration tricks
- Callback or transformation shortcuts
- Column naming conventions and gotchas

## Tip Structure
Each tip contains:
- **summary**: One-line description
- **context**: Where/how to apply the tip
- **example**: Code or configuration example
- **tags**: Categorization (ETL, transformation, smart_copy, etc.)
- **verified**: Whether the tip has been confirmed

## When to Use /tips
- You need a quick answer to "can I do X with Y?"
- Looking for verified workarounds or shortcuts
- Want to know about non-obvious parameter usage
- Need syntax examples for transformations or callbacks
- Checking for platform-specific gotchas

## Forbidden
- Mixing Tips with Database_Schema or IVALUA_Documentation in one search
- Calling mcp0_get_custom_data with null category or null key
- Relying on unverified tips for critical production configurations
- Using tips without understanding the underlying functionality

## Tips vs Documentation
- **Tips**: Quick verified discoveries, often discovered through experimentation
- **Documentation**: Official comprehensive guides and procedures
- **Tips complement documentation** - use tips for shortcuts, use documentation for complete understanding
