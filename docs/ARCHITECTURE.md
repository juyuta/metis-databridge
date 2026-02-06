# Architecture & Technical Reference

This document covers the technical design of Metis DataBridge. For strategic vision and philosophy, see [README.md](/README.md).

---

## Core Principles

- **Metadata-driven** - Pipelines defined via configuration, not code changes
- **Connector-light** - Start with a small, generic connector set
- **Composable** - Sources, transformations, and sinks are loosely coupled
- **Repeatable** - Pipelines can be rerun deterministically
- **Extensible** - New connectors and rules can be added without core rewrites

---

## High-Level Architecture

Metis is composed of the following conceptual layers:

- **Metadata Layer** - Configuration definitions (YAML, CSV, SQL)
- **Execution Engine** - Reads metadata and constructs data pipelines
- **Transformation Engine** - Applies mapping, rules, and SQL transformations
- **Orchestration Layer** - Manages pipeline execution flow
- **Connectors** - Source and sink adapters
- **Validation Layer** - Data quality checks
- **Monitoring Layer** - Operational logs & audits

### Execution Flow

```
Source → Extract → Load → Transform → Validate → Report
         (DataFrame) (Landing Table) (In-Memory/SQL) (Checks)
```

---

## Supported Systems

### Current (v0.1.0)

**Sources:**
- PostgreSQL (full support - schema detection, parameterized queries)

**Sinks:**
- PostgreSQL (full support - table creation, upsert, transactions)

**Transformation:**
- CSV-based column mapping (metadata-driven)
- Rule-based transformations (Python, in-memory)
- SQL transformations (server-side, multi-step with dependencies)

**Validation:**
- Row count checks
- Null/not-null validation
- Duplicate detection
- Custom validation rules

### Planned

**Sources:**
- CSV files
- Parquet files
- MySQL
- Snowflake
- BigQuery
- Redshift

**Sinks:**
- CSV files
- Parquet files
- Cloud warehouses

**Features:**
- Change Data Capture (CDC)
- Spark execution mode
- Airflow integration

---

## Configuration Model

All pipelines are defined in YAML format.

### Example Structure

```yaml
pipeline:
  name: customer_migration
  description: Migrate and deduplicate customers

source:
  type: PostgreSQL
  config:
    database: legacy_db
    table: customers
    # Optional: custom query
    # query: SELECT * FROM customers WHERE status = 'active'

sink:
  type: PostgreSQL
  config:
    database: analytics_db
    table: customers_clean

# Optional: Column mapping (CSV file)
mapping_file: mappings.csv

# Optional: SQL transformations
sql_transform_file: transformations.sql

# Optional: Data validation rules
validations:
  - type: row_count
  - type: null_check
    column: customer_id
  - type: duplicate_check
    columns: [id, email]
```

---

## Transformation Layers

### Layer 1: CSV Mapping (Metadata)

**File:** `mappings.csv`

```csv
source_column,target_column,target_data_type,precision,scale,nullable,default_value
cust_id,id,INTEGER,,,false,
cust_name,name,VARCHAR(255),,,true,
balance,amount,DECIMAL,18,2,true,0.00
created_ts,created_at,TIMESTAMP,,,false,
status,status_code,INTEGER,,,true,0
```

**Features:**
- Column renaming
- Data type conversion
- Precision/scale for decimals
- Nullable constraints
- Default values
- Non-technical (analysts can maintain)

### Layer 2: Rule-Based Transformations

**Type:** Python, in-memory

**Rules:**
- `Rename` - Rename columns
- `Cast` - Type conversion
- `Filter` - Row filtering (WHERE clause)
- `Replace` - Value replacement
- `Map` - Value mapping (lookup table)
- `Default` - Set defaults

**Configuration:**
```yaml
transformations:
  - type: filter
    condition: "status == 'active'"
  
  - type: cast
    column: created_date
    to: date
  
  - type: replace
    column: status_code
    from: 'PENDING'
    to: 'INACTIVE'
```

**Performance:** Good for < 100K rows, slower for large datasets

### Layer 3: SQL Transformations

**File:** `transformations.sql`

**Format:** Declarative SQL with special markers

```sql
-- @step: Deduplicate
-- @description: Remove duplicate customers, keep latest
SELECT DISTINCT ON (id) *
FROM ${LANDING_TABLE}
ORDER BY id, created_at DESC;

-- @step: Enrich
-- @description: Add customer segment
-- @depends_on: Deduplicate
SELECT c.*,
  CASE
    WHEN c.balance > 10000 THEN 'PREMIUM'
    ELSE 'STANDARD'
  END as segment
FROM dedup_customers c;

-- @step: Final Load
-- @final
-- @depends_on: Enrich
INSERT INTO ${TARGET_TABLE}
SELECT * FROM enriched_customers;
```

**Features:**
- Multi-step transformations
- Dependency management
- Variable substitution (`${LANDING_TABLE}`, `${TARGET_TABLE}`)
- Server-side execution (20-30x faster)
- Full SQL power (joins, aggregations, window functions)

**Performance:** 20-30x faster than Python for 1M+ rows

---

## Validation Framework

### Built-In Validators

**Row Count Validation:**
```yaml
validations:
  - type: row_count
    expected: 50000        # Exact count or within range
    or_range: [49000, 51000]
```

**Null Validation:**
```yaml
validations:
  - type: null_check
    column: customer_id
    expected: 0            # Expect 0 nulls
```

**Duplicate Validation:**
```yaml
validations:
  - type: duplicate_check
    columns: [id, email]
    expected: 0
```

**Custom Validation:**
```python
class CustomValidator(ValidationRule):
    def validate(self, dataset: DataSet) -> ValidationResult:
        # Custom logic
        return ValidationResult(passed=True, message="OK")
```

### Validation Levels

- `ERROR` - Pipeline fails if validation fails
- `WARNING` - Pipeline continues but marks data quality issue
- `INFO` - Informational, no action taken

---

## Connector Interface

### Source Interface

```python
class Source(ABC):
    def connect(self) -> None:
        """Establish connection to source"""
        
    def disconnect(self) -> None:
        """Close connection"""
        
    def get_schema(self, table: str) -> Schema:
        """Get table metadata"""
        
    def extract(self, table: str, query: str = None) -> DataSet:
        """Extract data from source"""
```

### Sink Interface

```python
class Sink(ABC):
    def connect(self) -> None:
        """Establish connection to sink"""
        
    def disconnect(self) -> None:
        """Close connection"""
        
    def load(self, dataset: DataSet, table: str) -> int:
        """Load data to sink, return row count"""
        
    def create_table(self, schema: Schema, table: str) -> None:
        """Create table from schema"""
```

### Adding a New Connector

```python
from connectors.base import Source, Sink

class MySQLSource(Source):
    def __init__(self, config: dict):
        self.config = config
        self.connection = None
    
    def connect(self):
        # MySQL connection logic
        pass
    
    def get_schema(self, table: str) -> Schema:
        # Query information_schema
        pass
    
    def extract(self, table: str, query: str = None) -> DataSet:
        # Execute query, return DataFrame as DataSet
        pass
    
    def disconnect(self):
        # Close connection
        pass

# Register connector
from connectors.base import ConnectorRegistry
ConnectorRegistry.register('MySQL', MySQLSource, MySQLSink)

# Use in YAML
# source:
#   type: MySQL
#   config:
#     host: localhost
#     database: mydb
#     table: users
```

---

## Data Models

### DataType Enum

```python
class DataType(Enum):
    STRING = "STRING"           # VARCHAR, TEXT
    INTEGER = "INTEGER"         # INT, BIGINT
    FLOAT = "FLOAT"            # FLOAT, DOUBLE
    DECIMAL = "DECIMAL"        # NUMERIC, DECIMAL
    DATE = "DATE"              # DATE
    DATETIME = "DATETIME"      # TIMESTAMP
    BOOLEAN = "BOOLEAN"        # BOOLEAN
    JSON = "JSON"              # JSON, JSONB
    BYTES = "BYTES"            # BYTEA
```

### Column

```python
@dataclass
class Column:
    name: str
    data_type: DataType
    nullable: bool = True
    precision: int = None      # For DECIMAL
    scale: int = None          # For DECIMAL
```

### Schema

```python
@dataclass
class Schema:
    table: str
    columns: List[Column]
```

### DataSet

```python
@dataclass
class DataSet:
    schema: Schema
    data: pd.DataFrame         # Pandas DataFrame
    row_count: int
```

---

## Execution Lifecycle

### Pipeline Execution Stages

1. **Load Configuration** - Parse YAML, load mapping file
2. **Instantiate Connectors** - Create source & sink instances
3. **Connect** - Establish connections to source & sink
4. **Extract** - Read data from source, store in DataFrame
5. **Load to Landing** - Write to temporary landing table in sink
6. **Apply Mappings** - CSV column transformations
7. **Apply Rules** - Rule-based transformations (in-memory)
8. **Apply SQL** - SQL transformations (server-side)
9. **Validate** - Run validation rules
10. **Report** - Generate execution summary
11. **Disconnect** - Close all connections

### Execution Report

```json
{
  "pipeline_name": "customer_migration",
  "status": "SUCCESS",
  "start_time": "2026-02-06T10:30:00Z",
  "end_time": "2026-02-06T10:30:45Z",
  "duration_seconds": 45.2,
  "rows_extracted": 50000,
  "rows_loaded": 50000,
  "rows_transformed": 50000,
  "validation_results": [
    {
      "rule": "row_count",
      "passed": true,
      "level": "ERROR",
      "message": "Row count validation passed: 50000 rows"
    }
  ],
  "execution_log": [
    {
      "timestamp": "2026-02-06T10:30:00Z",
      "level": "INFO",
      "message": "Starting pipeline: customer_migration"
    }
  ]
}
```

---

## Performance Characteristics

### Tested on 1M Row Dataset

| Operation | Method | Time | Notes |
|-----------|--------|------|-------|
| Extract | PostgreSQL | 2.1s | Network + DataFrame conversion |
| Load | PostgreSQL | 1.8s | Bulk insert to landing table |
| CSV Mapping | Python | 45.2s | Row-by-row processing |
| SQL Transform (dedup) | PostgreSQL | 0.8s | DISTINCT ON |
| SQL Transform (enrich) | PostgreSQL | 3.2s | 10M row join |
| Validation | Python | 2.1s | Row count, null checks |

### Recommendations

- **< 100K rows:** Rule-based transformations OK
- **100K - 1M rows:** Prefer SQL transformations
- **> 1M rows:** Must use SQL transformations
- **> 1B rows:** Future - Spark execution mode

---

## Error Handling

### Structured Error Reporting

All errors include:
- Clear error message
- Pipeline stage where error occurred
- Detailed exception info (for debugging)
- Partial execution status (what succeeded before failure)

### Retry Logic

Current version: No automatic retry (planned for v0.2)

Future: Configurable retry with exponential backoff

---

## Extensibility

### Add a Custom Validation Rule

```python
from pipelines.validation import ValidationRule, ValidationResult

class BalanceThresholdRule(ValidationRule):
    """Check that all balances are positive"""
    
    rule_name = "balance_threshold"
    
    def __init__(self, column: str, min_value: float):
        self.column = column
        self.min_value = min_value
    
    def validate(self, dataset: DataSet) -> ValidationResult:
        invalid_rows = (dataset.data[self.column] < self.min_value).sum()
        passed = invalid_rows == 0
        
        return ValidationResult(
            passed=passed,
            rule_name=self.rule_name,
            message=f"{invalid_rows} rows have {self.column} < {self.min_value}"
        )
```

### Add a Custom Transformation Rule

```python
from pipelines.transformations import TransformationRule

class CustomRule(TransformationRule):
    rule_type = "custom"
    
    def transform_row(self, row: DataRow) -> DataRow:
        # Custom logic
        row['new_field'] = some_calculation(row)
        return row
```

---

## Directory Structure

```
metis-databridge/
├── src/
│   ├── __init__.py
│   ├── main.py                    # CLI entry point
│   ├── config/
│   │   ├── __init__.py
│   │   └── loader.py              # YAML config parser
│   ├── connectors/
│   │   ├── __init__.py
│   │   ├── base.py                # Abstract classes
│   │   └── postgres.py            # PostgreSQL implementation
│   ├── pipelines/
│   │   ├── __init__.py
│   │   ├── orchestrator.py        # Pipeline execution
│   │   ├── transformations.py     # Rule-based transforms
│   │   ├── mapping.py             # CSV mapping
│   │   ├── sql_transform.py       # SQL transformation engine
│   │   └── validation.py          # Validation rules
│   ├── metadata/                  # (Placeholder)
│   ├── models/                    # (Placeholder)
│   ├── runners/                   # (Placeholder)
│   ├── services/                  # (Placeholder)
│   └── utils/                     # (Placeholder)
├── jobs/                          # Example pipelines
│   ├── 01_customer_migration_simple/
│   ├── 02_customer_migration_full/
│   └── 03_orders_incremental/
├── docs/                          # Documentation
├── tests/unit/                    # Unit tests (coming soon)
└── README.md
```

---

## CLI Interface

### Usage

```bash
# Run by job name
python src/main.py 01_customer_migration_simple -v

# Run by full path
python src/main.py jobs/my_job/pipeline.yml -v

# Generate report
python src/main.py my_job --report report.json

# Debug mode
python src/main.py my_job --verbose
```

### Arguments

- `config` - Job name or path to pipeline.yml
- `--report, -r` - Path to save execution report JSON
- `--verbose, -v` - Enable debug logging

---

## Engineering Standards

**Language:** Python 3.10+  
**Type Checking:** Pylance  
**Linting:** ruff (built-in)  
**Testing:** pytest (coming soon)  
**Configuration:** YAML  
**Logging:** Python logging module  
**Version Control:** Git (trunk-based)  

---

## Future Architecture Enhancements

### Phase 3: Enterprise Features
- Lineage tracking (column-level)
- Advanced validation rules (custom SQL)
- Performance optimization hints

### Phase 4: Ecosystem
- Spark execution mode (distributed)
- Airflow operator
- REST API for programmatic execution
- Web UI for monitoring

---

For strategic vision and philosophy, see [README.md](README.md).
