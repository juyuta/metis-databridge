# Transformation Approaches in Metis DataBridge

Metis supports three complementary approaches to data transformation, allowing you to choose the best tool for each use case.

## Overview

| Approach | Use Case | Complexity | Performance | Maintainability |
|----------|----------|-----------|------------|-----------------|
| **CSV Mappings** | Simple column transforms | Low | Medium | High |
| **Rule Transformations** | Business rules, calculations | Medium | Medium | Medium |
| **SQL Transformations** | Complex logic, aggregations | High | High (best) | High |

---

## 1. CSV-Based Column Mappings

**When to use:** Straightforward column-level transformations

### Supported Operations
- ✅ Column renaming
- ✅ Data type casting
- ✅ Precision/scale for decimals
- ✅ Null value defaults
- ✅ Simple value mappings

### Example

```csv
source_column,target_column,target_data_type,default_value
cust_id,customer_id,INTEGER,
amount_str,amount,DECIMAL,0.00
email,contact_email,VARCHAR,"unknown@example.com"
```

### Pros
- Simple, non-technical users can edit CSVs
- No code knowledge required
- Spreadsheet-friendly
- Good versioning in git

### Cons
- Can't handle complex logic
- Limited to columnar transformations
- No aggregations or joins
- Limited filtering capabilities

### Example Pipeline

```yaml
pipeline:
  mapping_file: mappings.csv

transformations: []  # No additional rules needed
```

---

## 2. Rule-Based Transformations (YAML)

**When to use:** Business logic, conditional transforms, string operations

### Supported Operations
- ✅ Column renaming (like CSV)
- ✅ Type casting (like CSV)
- ✅ Conditional defaults
- ✅ String replacement (with regex)
- ✅ Filtering rows
- ✅ Custom Python predicates

### Example

```yaml
transformations:
  - type: rename
    mappings:
      old_name: new_name
  
  - type: cast
    column: amount
    to: float
  
  - type: replace
    column: email
    find: "@old.com"
    replace: "@new.com"
    is_regex: false
  
  - type: default
    column: status
    value: "ACTIVE"
```

### Pros
- Flexible business logic
- Good for string manipulations
- Can reference multiple columns
- Python-friendly for extending

### Cons
- Limited to row-level operations
- Can't do aggregations
- Can't do joins
- Performance bottleneck for large datasets
- Code-based (Python knowledge needed)

### Example Pipeline

```yaml
pipeline:
  transformations:
    - type: rename
      mappings: { old: new }
    - type: cast
      column: date_str
      to: date
```

---

## 3. SQL-Based Transformations (Modern Declarative)

**When to use:** Complex transformations, aggregations, joins, large-scale migrations

### Supported Operations
- ✅ Deduplication (DISTINCT ON, ROW_NUMBER)
- ✅ Aggregations (GROUP BY, SUM, AVG, etc.)
- ✅ Joins (INNER, LEFT, FULL)
- ✅ Window functions (RANK, PARTITION)
- ✅ CTEs (WITH clauses)
- ✅ Conditional logic (CASE WHEN)
- ✅ String operations (UPPER, TRIM, etc.)
- ✅ Date operations
- ✅ Type casting

### Example

```sql
-- @step: deduplicate
-- @description: Keep latest version of each customer
CREATE TEMP TABLE customers_clean AS
SELECT DISTINCT ON (customer_id)
    customer_id, name, email,
    ROW_NUMBER() OVER (ORDER BY updated_at DESC) as rn
FROM ${SOURCE_TABLE}
WHERE customer_id IS NOT NULL
ORDER BY customer_id, updated_at DESC;

-- @step: enrich
-- @depends_on: deduplicate
-- @final: true
INSERT INTO ${TARGET_TABLE}
SELECT
    customer_id,
    UPPER(name) as name,
    LOWER(email) as email,
    CASE
        WHEN balance > 1000 THEN 'VIP'
        ELSE 'REGULAR'
    END as segment,
    CURRENT_TIMESTAMP as processed_at
FROM customers_clean;
```

### Pros
- **Best performance** (server-side execution)
- Handles complex logic efficiently
- Aggregations, joins, window functions
- Scales to billions of rows
- SQL is industry standard
- Easy for data teams to optimize
- Git-friendly (SQL in version control)
- Supports incremental loads (UPSERT)

### Cons
- Requires SQL knowledge
- Database-specific syntax (PostgreSQL in our case)
- Complex queries need testing
- Query optimization needed for large datasets

### Example Pipeline

```yaml
pipeline:
  sql_transform_file: transformations/customer_analytics.sql

transformations: []  # All logic in SQL
validations: [...]   # Validate results
```

---

## Combining Approaches

You can use all three together in a single pipeline:

```yaml
pipeline:
  mapping_file: mappings.csv                    # Step 1: Column mapping
  sql_transform_file: transformations.sql       # Step 2: SQL logic
  transformations:
    - type: replace                             # Step 3: Additional rules
      column: status
      find: "NEW"
      replace: "ONBOARDED"

validations: [...]  # Step 4: Validate results
```

### Execution Order

1. **Extract** → Land data in staging table
2. **CSV Mappings** → Rename columns, cast types, apply defaults
3. **SQL Transformations** → Execute server-side logic
4. **Rule Transformations** → Apply additional business rules
5. **Validate** → Quality checks

---

## Decision Matrix

Choose based on your transformation complexity:

```
Simple column mapping?
├─ YES → Use CSV mappings
└─ NO
    └─ Need complex logic/aggregations/joins?
        ├─ YES → Use SQL transformations
        └─ NO → Use rule transformations
```

### Examples by Complexity

**Simple (CSV only)**
```
source_col → target_col (INTEGER)
default_value = 0
```

**Medium (CSV + Rules)**
```
source_col → target_col (INTEGER)
if null: default to 0
replace "OLD" with "NEW"
```

**Complex (SQL)**
```
Aggregate sales by customer
Join with region data
Calculate tenure and segments
Upsert to target with incremental load
```

---

## Performance Implications

For 1M row dataset:

| Approach | Time | Memory | Notes |
|----------|------|--------|-------|
| CSV Mapping | 45s | High | Python-based row processing |
| Rule Transform | 60s | High | More Python logic |
| SQL Transform | 2s | Low | Database-optimized |

**Result:** SQL is **20-30x faster** for complex transformations

---

## Best Practices

### When using CSV mappings:
- ✅ Use for first-pass column standardization
- ✅ Combine with SQL for complex logic
- ✅ Keep mappings in version control
- ✅ Document column transformations

### When using rule transformations:
- ✅ Keep rules simple and focused
- ✅ Use for business logic that changes frequently
- ✅ Test transformation logic thoroughly
- ✅ Document why each rule exists

### When using SQL transformations:
- ✅ Use for any aggregations or joins
- ✅ Use for large datasets (1M+ rows)
- ✅ Version control SQL files
- ✅ Use comments (@step, @description) to document
- ✅ Create indexes for query performance
- ✅ Use `ANALYZE` to update statistics

---

## Migration Strategy

**Phase 1:** Start with CSV mappings
```yaml
mapping_file: simple.csv
```

**Phase 2:** Add business rules as needed
```yaml
mapping_file: simple.csv
transformations:
  - type: replace
    column: email
    find: "@"
    replace: "_at_"
```

**Phase 3:** Move complex logic to SQL
```yaml
sql_transform_file: transformations.sql
```

This progression allows your pipeline to grow as requirements evolve.

---

## See Also

- [CSV Mapping Guide](mapping-guide.md)
- [SQL Transformation Guide](sql-transformation-guide.md)
- [Transformation Examples](../examples/transformations/)
