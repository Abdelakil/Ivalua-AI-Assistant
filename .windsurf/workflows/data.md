---
description: Query database schema only (no documentation)
---

# /data - Database Schema Query

Use this command when you need information about Ivalua database tables, columns, relationships, or data model.

## Instructions

**Scope Restriction:**
- ONLY use the `Database_Schema` category in ConPort searches
- NEVER include `IVALUA_Documentation` in searches
- ALWAYS check column names before using them in queries, NEVER assume column names.
- This prevents documentation prose from contaminating technical schema results

## Search Patterns

1. **Table name known** (e.g., 't_bas_legal_company'):
   - Use: `mcp0_get_custom_data(category='Database_Schema', key='TABLE_BAS_T_BAS_LEGAL_COMPANY')`
   - NEVER omit category or key (dumps entire DB)

2. **Module known, listing tables**:
   - Use: `mcp0_get_custom_data(category='Database_Schema', key='MODULE_BAS')`

3. **All modules overview**:
   - Use: `mcp0_get_custom_data(category='Database_Schema', key='MODULE_INDEX')`

4. **Semantic schema search** (fuzzy table/column lookup):
   - Use: `mcp0_semantic_search_conport(filter_item_types=['custom_data'], filter_custom_data_categories=['Database_Schema'])`
   - MUST scope to Database_Schema only

5. **FTS schema search** (partial strings):
   - Use: `mcp0_search_custom_data_value_fts(query_term='...', category_filter='Database_Schema')`

## Forbidden
- Mixing Database_Schema + IVALUA_Documentation in one search
- Calling mcp0_get_custom_data with null category or null key
- Relying on memory/training data for table/column names; always fetch from ConPort

### Writing rules
- **SQL Server syntax only** (T-SQL): use `GETDATE()`, `TOP`, `ISNULL`, `[brackets]` for reserved words, etc. No MySQL/PostgreSQL syntax.
- **Minimum joins**: include a table only if one of its columns appears in SELECT, WHERE, or is required for a FK path. Never join "just in case".
- **Label/name columns**: always use the `_!$` suffix for translated label fields.
  - Correct: `sup.sup_name_!$`, `ctr.ctr_label_!$`, `com.com_label_!$`
  - Wrong: `sup.sup_name_en`, `sup.sup_name`
- **Aliases**: always alias tables with the short module prefix (`sup`, `ctr`, `ord`, `bsk`, `adr`, etc.) and qualify every column with its alias.
- **System variables in callbacks**: use Ivalua-provided variables (`@sup_id`, `@basket_id`, `@ctr_id`, `@imp_id`, `@contact_id_current`, `@login_name_current`, `@otype_code`, `@timestamp`, `@x_id`). Do not invent new ones.
