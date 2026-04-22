---
description: Query database schema with selective documentation modules
---

# /mix - Hybrid Schema + Documentation Query

Use this command when you need both database schema information AND specific documentation modules. This allows you to combine technical data model with functional context from selected documentation areas.

## Instructions

**Scope Restriction:**
- ALWAYS include `Database_Schema` category
- Selectively include specific `IVALUA_Documentation` modules only
- Selectively include `Tips` category for quick gotchas / verified facts
- Specify which documentation/tips modules are relevant to the query
- ALWAYS check column names before using them in queries, NEVER assume column names.

## Search Patterns

**Database Schema (always included):**
1. Table name known: `mcp0_get_custom_data(category='Database_Schema', key='TABLE_{MODULE}_{TABLE}')`
2. Module tables: `mcp0_get_custom_data(category='Database_Schema', key='MODULE_{CODE}')`
3. All modules: `mcp0_get_custom_data(category='Database_Schema', key='MODULE_INDEX')`
4. Semantic search: `mcp0_semantic_search_conport(filter_item_types=['custom_data'], filter_custom_data_categories=['Database_Schema'])`
5. FTS search: `mcp0_search_custom_data_value_fts(query_term='...', category_filter='Database_Schema')`

**Documentation (selective):**
1. Specific module: `mcp0_get_custom_data(category='IVALUA_Documentation', key='DOC_INDEX_{MODULE_SLUG}')`
   - Examples: DOC_INDEX_SUPPLIER_MANAGEMENT, DOC_INDEX_SOURCING, DOC_INDEX_CONTRACT_MANAGEMENT
2. Semantic search with module filter: `mcp0_semantic_search_conport(filter_item_types=['custom_data'], filter_custom_data_categories=['Database_Schema', 'IVALUA_Documentation'])`
   - Use only for modules you've identified as relevant
3. FTS with module filter: `mcp0_search_custom_data_value_fts(query_term='...', category_filter='IVALUA_Documentation')`
   - Limit to relevant documentation topics

**Tips (selective):**
1. All tips: `mcp0_get_custom_data(category='Tips', key='TIPS_INDEX')`
2. FTS search: `mcp0_search_custom_data_value_fts(query_term='...', category_filter='Tips')`
3. Semantic search: `mcp0_semantic_search_conport(filter_item_types=['custom_data'], filter_custom_data_categories=['Tips'])`

**Query strategy:**
- Start with schema to get correct table/column names
- Use documentation to understand business logic, configuration steps, or functional behavior
- Use Tips for quick verified gotchas (column naming, syntax traps, parameter quirks)
- NEVER mix categories in a single semantic/FTS search — query them separately

## When to Use /mix
- You need both technical schema AND business process context
- The documentation is specific to the schema area (e.g., Contract schema + Contract documentation)
- You need to understand how a table/column is used in the application
- Configuration questions that require both data model and functional knowledge

## Common Module Slugs
- SUPPLIER_MANAGEMENT
- SOURCING
- CONTRACT_MANAGEMENT
- E_PROCUREMENT
- INVOICING
- PLATFORM_ADMIN_AND_CONFIG

## Forbidden
- Including all documentation modules indiscriminately (use /docu for that)
- Calling mcp0_get_custom_data with null category or null key
- Mixing unrelated documentation with schema (causes hallucinations)

### Writing rules
- **SQL Server syntax only** (T-SQL): use `GETDATE()`, `TOP`, `ISNULL`, `[brackets]` for reserved words, etc. No MySQL/PostgreSQL syntax.
- **Minimum joins**: include a table only if one of its columns appears in SELECT, WHERE, or is required for a FK path. Never join "just in case".
- **Label/name columns**: always use the `_!$` suffix for translated label fields.
  - Correct: `sup.sup_name_!$`, `ctr.ctr_label_!$`, `com.com_label_!$`
  - Wrong: `sup.sup_name_en`, `sup.sup_name`
- **Aliases**: always alias tables with the short module prefix (`sup`, `ctr`, `ord`, `bsk`, `adr`, etc.) and qualify every column with its alias.
- **System variables in callbacks**: use Ivalua-provided variables (`@sup_id`, `@basket_id`, `@ctr_id`, `@imp_id`, `@contact_id_current`, `@login_name_current`, `@otype_code`, `@timestamp`, `@x_id`). Do not invent new ones.
