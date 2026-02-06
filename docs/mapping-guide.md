# Column Mapping Guide

Metis DataBridge supports **CSV-based column mappings** for metadata-driven data transformations. This allows non-technical users to define complex transformations without writing code.

## Quick Start

### 1. Create a Mapping CSV File

```csv
source_column,target_column,source_data_type,target_data_type,nullable,default_value,description
id,customer_id,INTEGER,INTEGER,false,,Customer unique ID
name,customer_name,VARCHAR,VARCHAR,true,,"Full name"
email,email_address,VARCHAR,VARCHAR,false,"unknown@example.com",Contact email
```

### 2. Reference in Pipeline YAML

```yaml
pipeline:
  name: my_pipeline
  mapping_file: path/to/mappings.csv

source:
  type: postgres
  config:
    table: source_customers

sink:
  type: postgres
  config:
    table_name: target_customers
```

### 3. Run the Pipeline

```bash
python src/main.py pipeline.yml --report report.json
```

## CSV Column Reference

### Required Columns

| Column | Description | Example |
|--------|-------------|---------|
| `source_column` | Name of column in source system | `cust_id` |
| `target_column` | Name of column in target system | `customer_id` |

### Optional Columns

| Column | Description | Example |
|--------|-------------|---------|
| `source_data_type` | Data type in source | `VARCHAR`, `INTEGER`, `DECIMAL` |
| `target_data_type` | Data type in target | `VARCHAR`, `INTEGER`, `DECIMAL` |
| `source_precision` | For numeric types: total digits | `10` |
| `source_scale` | For numeric types: decimal places | `2` |
| `target_precision` | For numeric types: total digits | `12` |
| `target_scale` | For numeric types: decimal places | `2` |
| `nullable` | Allow NULL values? | `true`, `false` |
| `default_value` | Value if source is NULL | `0`, `"N/A"` |
| `transformation_rule` | Custom rule name (future) | `custom_rule_1` |
| `description` | Human-readable notes | `Account creation date` |

## Supported Data Types

- `STRING` / `VARCHAR`
- `INTEGER` / `BIGINT`
- `FLOAT` / `DOUBLE`
- `DECIMAL` / `NUMERIC`
- `BOOLEAN`
- `DATE`
- `DATETIME` / `TIMESTAMP`
- `BYTES`
- `JSON` / `JSONB`

## Transformation Order

When both mappings (CSV) and transformations (YAML) are configured:

1. **Mapping Transformations** (applied first)
   - Column renaming (source → target)
   - Type casting
   - Default value application
   - Precision/scale adjustments

2. **Rule Transformations** (applied second)
   - Custom transformation rules from YAML
   - Additional business logic
   - String manipulation, filtering, etc.

3. **Validation** (applied last)
   - Data quality checks

## Examples

### Simple Column Rename

```csv
source_column,target_column
legacy_id,id
legacy_name,name
```

### With Type Casting

```csv
source_column,target_column,source_data_type,target_data_type
amount_str,amount,VARCHAR,DECIMAL
date_str,transaction_date,VARCHAR,DATE
active_flag,is_active,VARCHAR,BOOLEAN
```

### With Precision/Scale (Decimals)

```csv
source_column,target_column,source_data_type,target_data_type,source_precision,source_scale,target_precision,target_scale
amount,account_balance,NUMERIC,DECIMAL,10,2,12,2
```

### With Default Values

```csv
source_column,target_column,nullable,default_value
email,contact_email,false,"unknown@example.com"
country,region,true,"US"
status,is_active,false,false
```

### Complete Example

See `examples/customer_mapping.csv` and `examples/customer_migration_with_mapping.yml`

## Data Type Casting

The mapping engine automatically casts values when target type differs from source:

- **STRING** → Other types: parsed appropriately
- **INTEGER/FLOAT** → STRING: converted via string representation
- **DECIMAL**: Respects precision and scale
- **DATE/DATETIME**: Parsed from ISO format strings
- **BOOLEAN**: "true", "1", "yes", "y" → True; others → False
- **NULL values**: Replaced with default_value if specified

## Performance Considerations

- Mappings are loaded once at pipeline startup
- Type casting happens row-by-row during transformation
- For large datasets (>1M rows), consider batch processing
- CSV loading is O(n) where n = number of columns

## Troubleshooting

### Mapping file not found

```
ERROR: Mapping file not found: path/to/file.csv
```

→ Check file path is relative to working directory or absolute

### Unknown data type

```
WARNING: Unknown source data type: CUSTOM_TYPE
```

→ Use standard SQL type names (see Supported Data Types section)

### Column not found in mapping

If a source column isn't in the CSV mapping, it will be kept as-is in the target (no renaming or casting).

### Type casting failed

```
WARNING: Failed to cast 'abc' to INTEGER
```

→ Check data quality in source. Consider using validation rules to catch these cases.
