# Customer Migration - Full Example

Complete end-to-end example showcasing all Metis DataBridge features.

## What This Does

1. **Extract** - Reads from legacy PostgreSQL
2. **Load** - Writes to landing table
3. **Map** - CSV-based column transformations (rename, type, defaults)
4. **Transform** - SQL-based business logic (dedup, enrich, segment)
5. **Validate** - Comprehensive data quality checks

## Files

- `pipeline.yml` - Pipeline configuration with all options
- `mappings.csv` - Column-level metadata-driven transformations
- `transformations.sql` - Complex SQL transformation logic
- `README.md` - This file

## Running This Example

```bash
python src/main.py examples/02_customer_migration_full/pipeline.yml \
  --report report.json \
  -v
```

## Files Explained

### `pipeline.yml`
- References mapping file for column transformations
- References SQL file for business logic
- Defines validation rules
- Configures source and sink connections

### `mappings.csv`
Metadata-driven column transformations:
```csv
source_column,target_column,target_data_type,nullable,default_value
cust_id,customer_id,INTEGER,false,
amount_str,account_balance,DECIMAL,true,0.00
```

Non-technical users (analysts, DBAs) can edit this without touching code.

### `transformations.sql`
Complex transformation logic:
- Deduplication (DISTINCT ON)
- Enrichment (calculated fields)
- Segmentation (CASE WHEN)
- Validation (aggregations)

## Features Demonstrated

✅ Column mapping (CSV)
✅ SQL transformations (declarative)
✅ Row-level validations
✅ Null checks
✅ Duplicate detection
✅ Type casting
✅ Default values
✅ Calculated fields
✅ Customer segmentation

## Transformation Flow

```
Source Table
    ↓
Landing Table (raw extract)
    ↓
CSV Mappings Applied (rename, cast, defaults)
    ↓
SQL Transformations (dedup, enrich, segment)
    ↓
Target Table (analytics-ready)
    ↓
Validations (quality checks)
```

## Output Tables

- `landing_customers` - Raw extracted data
- `customers_analytics` - Final transformed data with:
  - Deduplication
  - Calculated fields (tenure, segment)
  - Customer segmentation

## Validation Results

The pipeline validates:
- Row count is > 0
- No NULL customer IDs
- No NULL emails
- No duplicate customer IDs
- No duplicate emails

## Next Steps

Try modifying:
1. `mappings.csv` - Add new column mappings
2. `transformations.sql` - Add more enrichment
3. `pipeline.yml` - Add new validation rules

See `03_orders_incremental` for incremental load patterns.
