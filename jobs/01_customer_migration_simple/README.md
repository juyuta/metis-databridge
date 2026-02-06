# Customer Migration - Simple Example

A minimal end-to-end example showing basic ELT workflow.

## What This Does

1. **Extract** - Reads customer data from legacy PostgreSQL
2. **Load** - Writes raw data to landing table
3. **Transform** - Basic deduplication and type casting via SQL
4. **Validate** - Checks row counts and required fields

## Files

- `pipeline.yml` - Pipeline configuration
- `transformations.sql` - SQL transformation steps

## Running This Example

```bash
# Ensure PostgreSQL source and target databases exist
# Update connection details in pipeline.yml

python src/main.py examples/01_customer_migration_simple/pipeline.yml \
  --report examples/01_customer_migration_simple/report.json \
  -v
```

## Output

- Landing table: `landing_customers` (raw extracted data)
- Target table: `customers_analytics` (transformed data)
- Report: `report.json` (execution summary)

## Key Concepts

- **ELT Pattern** - Extract, Load, then Transform
- **Server-side SQL** - Transformations run on database
- **Minimal Configuration** - Only essential components

## Next Steps

- See `02_customer_migration_full` for advanced features (mappings, validation)
- See `03_orders_incremental` for incremental load patterns
