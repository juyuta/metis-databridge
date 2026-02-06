# Metis DataBridge Jobs

This directory contains complete, runnable data pipeline jobs organized by workflow. Each directory contains a self-contained data pipeline with all necessary configuration files.

## Directory Structure

```
jobs/
├── 01_customer_migration_simple/    ← Start here!
│   ├── README.md
│   ├── pipeline.yml
│   └── transformations.sql
│
├── 02_customer_migration_full/      ← Complete feature showcase
│   ├── README.md
│   ├── pipeline.yml
│   ├── mappings.csv
│   └── transformations.sql
│
└── 03_orders_incremental/           ← Advanced patterns
    ├── README.md
    ├── pipeline.yml
    ├── mappings.csv
    └── transformations.sql
```

## Quick Start

### Prerequisites

```bash
# Install dependencies
pip install psycopg[binary] pyyaml pandas

# Create PostgreSQL databases for testing
createdb legacy_db
createdb analytics_db
```

### Running Jobs

```bash
# Simple job (easiest to understand)
python src/main.py 01_customer_migration_simple -v

# Full job (all features)
python src/main.py 02_customer_migration_full -v --report report.json

# Advanced job (incremental patterns)
python src/main.py 03_orders_incremental -v

# Using full paths (also works)
python src/main.py jobs/01_customer_migration_simple/pipeline.yml -v
```

## Job Overview

### 1️⃣ Customer Migration - Simple
**Complexity:** Beginner  
**Duration:** 5 min read  
**What you'll learn:**
- Basic ELT workflow
- SQL transformations
- Minimal configuration

**Best for:** First-time users, understanding the basics

### 2️⃣ Customer Migration - Full
**Complexity:** Intermediate  
**Duration:** 15 min read  
**What you'll learn:**
- Column mapping (CSV)
- SQL transformations
- Data validation
- Enrichment logic

**Best for:** Production-like scenarios, all features

### 3️⃣ Orders Incremental Load
**Complexity:** Advanced  
**Duration:** 20 min read  
**What you'll learn:**
- Incremental/UPSERT patterns
- Fact/Dimension tables
- Aggregations & metrics
- Window functions
- Complex joins

**Best for:** Data warehouse work, advanced SQL patterns

## Features Demonstrated

| Feature | Job 1 | Job 2 | Job 3 |
|---------|-----------|-----------|-----------|
| **ELT Workflow** | ✅ | ✅ | ✅ |
| **SQL Transforms** | ✅ | ✅ | ✅ |
| **Column Mapping** | ❌ | ✅ | ✅ |
| **Validation Rules** | ✅ | ✅ | ✅ |
| **Enrichment** | ❌ | ✅ | ✅ |
| **Aggregation** | ❌ | ❌ | ✅ |
| **Incremental Load** | ❌ | ❌ | ✅ |
| **Window Functions** | ❌ | ❌ | ✅ |

## File Structure in Each Job

### `pipeline.yml`
Main configuration file:
- Source connection details
- Sink connection details  
- References to mapping file (optional)
- References to SQL file
- Validation rules

### `mappings.csv` (optional)
Metadata-driven column transformations:
- Source → Target column mapping
- Data type conversions
- Precision/scale for decimals
- Nullable constraints
- Default values

### `transformations.sql`
Declarative SQL transformation logic:
- Multi-step transformations
- Deduplication, enrichment, aggregation
- Incremental load patterns
- Data quality checks
- Index creation

### `README.md`
Documentation for that specific job.

## Learning Path

1. **Start with Job 1**
   - Read the README
   - Review `pipeline.yml` structure
   - Run: `python src/main.py 01_customer_migration_simple`
   - Examine `transformations.sql`

2. **Move to Job 2**
   - Understand CSV mappings
   - See full feature set
   - Review complex SQL
   - Add validation rules

3. **Advance to Job 3**
   - Learn advanced SQL patterns
   - Fact/dimension tables
   - Incremental patterns
   - Performance optimization

## Customizing Jobs

### To adapt Job 1 for your data:

1. Copy the job:
   ```bash
   cp -r jobs/01_customer_migration_simple jobs/my_custom_job
   ```

2. Update `pipeline.yml`:
   ```yaml
   source:
     config:
       table: your_table_name
       database: your_database
   ```

3. Update `transformations.sql`:
   - Replace column names
   - Adjust transformation logic
   - Add your business rules

4. Run: `python src/main.py my_custom_job`

### To add column mapping:

1. Create `mappings.csv`:
   ```csv
   source_column,target_column,target_data_type
   old_id,id,INTEGER
   old_name,name,VARCHAR
   ```

2. Add to `pipeline.yml`:
   ```yaml
   mapping_file: mappings.csv
   ```

## Common Patterns

### Deduplication
```sql
SELECT DISTINCT ON (id) *
FROM source
ORDER BY id, updated_at DESC;
```

### Incremental Load (UPSERT)
```sql
INSERT INTO target SELECT * FROM source
ON CONFLICT (id) DO UPDATE SET
    amount = EXCLUDED.amount;
```

### Customer Segmentation
```sql
CASE
    WHEN balance > 10000 THEN 'PREMIUM'
    WHEN balance > 1000 THEN 'GOLD'
    ELSE 'SILVER'
END as segment
```

### Aggregation
```sql
SELECT
    customer_id,
    COUNT(*) as count,
    SUM(amount) as total
FROM orders
GROUP BY customer_id;
```

See [SQL Transformation Guide](../docs/sql-transformation-guide.md) for more patterns.

## Troubleshooting

### "Table does not exist"
- Check database connection in `pipeline.yml`
- Ensure landing table was created in load step
- Check table names in SQL file

### "Connection refused"
- Verify PostgreSQL is running: `psql --version`
- Check host/port in `pipeline.yml`
- Test connection: `psql -U postgres -h localhost`

### Mapping file not found
- Check path is relative to workspace root
- File should be at `jobs/XX_/mappings.csv`

### "SQL step failed"
- Check SQL syntax with `psql`
- Verify column names match source table
- Check constraints (PRIMARY KEY, UNIQUE)

## Performance Tips

- Use temporary tables for intermediate results
- Index on join/where columns
- Use `ANALYZE` for large tables
- Batch operations when possible
- Profile with `EXPLAIN ANALYZE`

## Next Steps

1. Choose an example matching your use case
2. Copy and customize for your data
3. Run and validate
4. Deploy to production

See:
- [SQL Transformation Guide](../docs/sql-transformation-guide.md)
- [Mapping Guide](../docs/mapping-guide.md)
- [Architecture Overview](../docs/architecture/overview.md)

Happy migrating! 🚀
