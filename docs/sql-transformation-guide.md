# SQL Transformation Guide

Metis DataBridge supports **declarative SQL-based transformations** for modern data engineering workflows. This allows you to leverage PostgreSQL's powerful query capabilities directly.

## Quick Start

### 1. Create a SQL Transformation File

```sql
-- @step: deduplicate
-- @description: Remove duplicate customer records
CREATE TEMP TABLE customers_clean AS
SELECT DISTINCT ON (customer_id)
    *
FROM ${SOURCE_TABLE}
ORDER BY customer_id, updated_at DESC;

-- @step: transform
-- @description: Apply business logic transformations
-- @depends_on: deduplicate
-- @final: true
INSERT INTO ${TARGET_TABLE}
SELECT
    customer_id,
    UPPER(customer_name) as customer_name,
    LOWER(email) as email,
    created_at::DATE as created_date,
    CURRENT_TIMESTAMP as processed_at
FROM customers_clean;
```

### 2. Reference in Pipeline YAML

```yaml
pipeline:
  name: customer_pipeline
  sql_transform_file: examples/transformations/customer_analytics.sql

source:
  type: postgres
  config:
    table: customers

sink:
  type: postgres
  config:
    table_name: customers_target
```

### 3. Run the Pipeline

```bash
python src/main.py pipeline.yml
```

## SQL File Format

### Step Markers

SQL files are divided into logical steps using special comments:

```sql
-- @step: step_name
-- @description: Human-readable description (optional)
-- @depends_on: previous_step_1, previous_step_2 (optional)
-- @final: true (optional - indicates final target table)

-- SQL code here...
```

### Markers Reference

| Marker | Purpose | Example |
|--------|---------|---------|
| `@step` | **Required** - unique step name | `@step: deduplicate` |
| `@description` | Optional - step documentation | `@description: Remove duplicates` |
| `@depends_on` | Optional - dependencies | `@depends_on: step1, step2` |
| `@final` | Optional - marks final output | `@final: true` |

### Variable Substitution

Metis provides automatic variable substitution for common table names:

| Variable | Replaced With | Usage |
|----------|---------------|-------|
| `${SOURCE_TABLE}` | Landing/staging table | Raw extracted data |
| `${TARGET_TABLE}` | Final target table | Business-ready data |
| `${LANDING_TABLE}` | Landing table (custom) | Intermediate data |

```sql
-- Using variables
SELECT * FROM ${SOURCE_TABLE};
INSERT INTO ${TARGET_TABLE} SELECT * FROM staging;
```

## Transformation Patterns

### Pattern 1: Deduplication

Keep only the latest version of each record:

```sql
-- @step: deduplicate
CREATE TEMP TABLE customers_dedup AS
SELECT DISTINCT ON (customer_id)
    *
FROM ${SOURCE_TABLE}
ORDER BY customer_id, updated_at DESC;
```

### Pattern 2: Data Cleaning

```sql
-- @step: clean_data
CREATE TEMP TABLE customers_clean AS
SELECT
    customer_id,
    TRIM(customer_name) as customer_name,
    LOWER(TRIM(email)) as email,
    CASE
        WHEN is_active IN ('Y', 'yes', '1') THEN true
        ELSE false
    END as is_active,
    balance::NUMERIC(12,2) as balance
FROM ${SOURCE_TABLE}
WHERE customer_id IS NOT NULL;
```

### Pattern 3: Data Enrichment

```sql
-- @step: enrich_data
-- @depends_on: clean_data
CREATE TEMP TABLE customers_enriched AS
SELECT
    *,
    CASE
        WHEN balance < 100 THEN 'LOW'
        WHEN balance < 1000 THEN 'MEDIUM'
        ELSE 'HIGH'
    END as value_tier,
    CURRENT_DATE - created_date::DATE as tenure_days
FROM customers_clean;
```

### Pattern 4: Aggregation

```sql
-- @step: aggregate_sales
CREATE TEMP TABLE customer_metrics AS
SELECT
    customer_id,
    COUNT(*) as transaction_count,
    SUM(amount) as total_spent,
    AVG(amount) as avg_transaction,
    MAX(transaction_date) as last_transaction
FROM ${SOURCE_TABLE}
GROUP BY customer_id;
```

### Pattern 5: Complex Joins

```sql
-- @step: enrich_with_region
-- @depends_on: clean_data
CREATE TEMP TABLE customers_with_region AS
SELECT
    c.*,
    r.region_name,
    r.timezone,
    r.currency
FROM customers_clean c
LEFT JOIN regions r ON c.region_id = r.region_id;
```

### Pattern 6: Window Functions

```sql
-- @step: rank_customers
CREATE TEMP TABLE customers_ranked AS
SELECT
    *,
    ROW_NUMBER() OVER (ORDER BY balance DESC) as balance_rank,
    RANK() OVER (PARTITION BY region_id ORDER BY balance DESC) as region_rank
FROM ${SOURCE_TABLE};
```

### Pattern 7: Incremental Load (UPSERT)

```sql
-- @step: upsert_to_target
-- @depends_on: enrich_data
-- @final: true
INSERT INTO ${TARGET_TABLE} (id, name, email, updated_at)
SELECT id, name, email, CURRENT_TIMESTAMP
FROM customers_enriched
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    email = EXCLUDED.email,
    updated_at = EXCLUDED.updated_at;
```

## Advanced Features

### Temporary Tables

Use `CREATE TEMP TABLE` for intermediate results that don't need to persist:

```sql
-- @step: step1
CREATE TEMP TABLE temp_intermediate AS
SELECT * FROM ${SOURCE_TABLE} WHERE status = 'ACTIVE';

-- @step: step2
-- @depends_on: step1
SELECT * FROM temp_intermediate;
```

### Common Table Expressions (CTEs)

```sql
-- @step: complex_transform
-- @final: true
INSERT INTO ${TARGET_TABLE}
WITH dedup AS (
    SELECT DISTINCT ON (id) * FROM ${SOURCE_TABLE} ORDER BY id, updated_at DESC
),
enriched AS (
    SELECT
        *,
        CASE WHEN balance > 1000 THEN 'VIP' ELSE 'REGULAR' END as segment
    FROM dedup
)
SELECT * FROM enriched;
```

### Data Validation in SQL

```sql
-- @step: validate_data
SELECT
    'row_count' as check_name,
    COUNT(*) as actual_count,
    CASE WHEN COUNT(*) > 0 THEN 'PASS' ELSE 'FAIL' END as status
FROM ${TARGET_TABLE}
UNION ALL
SELECT
    'nulls_in_key',
    COUNT(*) FILTER (WHERE id IS NULL),
    CASE WHEN COUNT(*) FILTER (WHERE id IS NULL) = 0 THEN 'PASS' ELSE 'FAIL' END
FROM ${TARGET_TABLE};
```

### Creating Indexes

```sql
-- @step: optimize
-- @depends_on: load_data
-- @final: true
CREATE INDEX idx_customer_email ON ${TARGET_TABLE}(email);
CREATE INDEX idx_customer_country ON ${TARGET_TABLE}(country);
ANALYZE ${TARGET_TABLE};
```

## Execution Order

SQL steps are executed sequentially in dependency order:

1. Steps with no dependencies execute first
2. Steps with `@depends_on` execute after their dependencies
3. Transaction handling ensures atomicity
4. On error, pipeline stops (can implement retry logic)

Example dependency chain:

```
validate_source
    ↓
deduplicate
    ↓
clean_data → enrich_data
    ↓
load_to_target (marked @final)
    ↓
create_indexes
```

## Performance Considerations

### Large Dataset Optimization

- Use **TEMP TABLE** for intermediate results to avoid disk I/O
- Batch operations when possible
- Use **DISTINCT ON** instead of window functions for dedup
- Index on join/where columns before aggregations

### Memory Usage

```sql
-- Good: Uses streaming
-- @step: large_dataset_load
INSERT INTO ${TARGET_TABLE}
SELECT * FROM ${SOURCE_TABLE} WHERE processed = false;

-- Avoid for large datasets: Creates intermediate table
-- @step: bad_approach
CREATE TABLE intermediate AS
SELECT * FROM huge_table
WHERE complex_condition;
```

### Monitoring

Check execution results in the report:

```json
{
  "stages": [{
    "stage": "transform",
    "status": "completed",
    "duration_seconds": 45.3,
    "record_count": 1000000
  }]
}
```

## Troubleshooting

### "Table does not exist"

Ensure table names are properly substituted:
- Check `${SOURCE_TABLE}` and `${TARGET_TABLE}` are being replaced
- Verify load step created the landing table

### "Step execution failed"

Check:
- SQL syntax errors
- Missing dependencies (use `@depends_on`)
- Permission issues on target table
- Constraint violations (e.g., UNIQUE key conflicts)

### Performance Issues

- Use `EXPLAIN ANALYZE` to profile queries
- Add indexes before large joins
- Use TEMP tables for intermediate results
- Batch inserts when possible

## Examples

See:
- `examples/transformations/customer_analytics.sql` - Comprehensive example
- `examples/transformations/customer_simple.sql` - Minimal example
- `examples/customer_migration_with_mapping.yml` - YAML configuration using SQL
