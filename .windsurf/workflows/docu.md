---
description: Query documentation only (no database schema)
---

# /docu - Documentation Query

Use this command when you need information about Ivalua functionality, processes, configuration, or business logic from the documentation.

## Instructions

**Scope Restriction:**
- ONLY use the `IVALUA_Documentation` category in ConPort searches
- NEVER include `Database_Schema` in searches
- This prevents technical schema identifiers from contaminating functional documentation results

## Search Patterns

1. **All documentation overview**:
   - Use: `mcp0_get_custom_data(category='IVALUA_Documentation', key='DOC_INDEX_ALL')`

2. **Documentation by module**:
   - Use: `mcp0_get_custom_data(category='IVALUA_Documentation', key='DOC_INDEX_{MODULE_SLUG}')`
   - Example: `DOC_INDEX_SUPPLIER_MANAGEMENT`, `DOC_INDEX_SOURCING`

3. **Semantic documentation search**:
   - Use: `mcp0_semantic_search_conport(filter_item_types=['custom_data'], filter_custom_data_categories=['IVALUA_Documentation'])`
   - MUST scope to IVALUA_Documentation only

4. **FTS documentation search**:
   - Use: `mcp0_search_custom_data_value_fts(query_term='...', category_filter='IVALUA_Documentation')`

## Use Cases
- How to configure features (alerts, workflows, EAI, ETL)
- Business process explanations
- Step-by-step procedures
- Best practices
- Functional requirements

## Forbidden
- Mixing IVALUA_Documentation + Database_Schema in one search
- Calling mcp0_get_custom_data with null category or null key
- Using database schema information to answer functional questions
