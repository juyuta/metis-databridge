# Orders Incremental Load - Advanced Example

Advanced example demonstrating incremental data loading patterns.

## What This Does

1. **Extract** - Reads new/modified orders from source
2. **Load** - Writes to landing table
3. **Transform** - Complex multi-step transformations:
   - Deduplication
   - Join with dimension tables
   - Aggregation and calculations
   - Incremental load (UPSERT)
4. **Validate** - Quality and volume checks

## Files

- `pipeline.yml` - Pipeline configuration
- `mappings.csv` - Column metadata
- `transformations.sql` - Advanced SQL patterns
- `README.md` - This file

## Running This Example

```bash
python src/main.py examples/03_orders_incremental/pipeline.yml \
  --report report.json
```

## Key Patterns Demonstrated

### 1. Incremental Load (UPSERT)
```sql
INSERT INTO target_table (id, amount, updated_at)
SELECT id, amount, CURRENT_TIMESTAMP
FROM staging
ON CONFLICT (id) DO UPDATE SET
    amount = EXCLUDED.amount,
    updated_at = EXCLUDED.updated_at;
```

### 2. Aggregations
```sql
SELECT
    customer_id,
    COUNT(*) as order_count,
    SUM(amount) as total_spent
FROM orders
GROUP BY customer_id;
```

### 3. Window Functions
```sql
SELECT
    *,
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) as recency
FROM orders;
```

### 4. Multi-table Enrichment
```sql
SELECT
    o.*,
    c.customer_name,
    c.segment,
    p.product_category
FROM orders o
LEFT JOIN customers c ON o.customer_id = c.id
LEFT JOIN products p ON o.product_id = p.id;
```

## Features

✅ Incremental loading (UPSERT)
✅ Fact/Dimension table patterns
✅ Aggregations and calculations
✅ Multi-table joins
✅ Window functions (row numbering, ranking)
✅ Change tracking

## Transformation Flow

```
Source Orders Table
    ↓
Landing (raw extract)
    ↓
Deduplication
    ↓
Join with Customers & Products
    ↓
Aggregate by Customer
    ↓
Calculate Order Metrics
    ↓
Incremental Load to Fact Table
    ↓
Validation
```

## Output Tables

- `landing_orders` - Raw extracted orders
- `fact_orders` - Fact table with dimension keys
- `orders_metrics` - Aggregated order metrics by customer

## Performance Considerations

- Uses indexes on join keys
- Temp tables for intermediate results
- Partitioning-ready design
- Incremental load avoids reprocessing

## Next Steps

- Modify mappings for your order schema
- Add more dimension joins (vendors, locations)
- Implement fact/dimension bus architecture
- Set up incremental load schedules
