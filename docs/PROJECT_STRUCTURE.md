# Complete Directory Structure

## Metis DataBridge Project Layout

```
metis-databridge/
│
├── README.md                          # Project overview
├── LICENSE                            # GNU v3.0
│
├── docs/                              # Documentation
│   ├── index.md                       # Documentation home
│   ├── architecture/
│   │   └── overview.md                # System architecture
│   ├── connectors/
│   │   └── postgres.md                # PostgreSQL connector docs
│   ├── guides/
│   │   ├── developer-guide.md
│   │   ├── getting-started.md
│   │   └── runbook.md
│   ├── metadata/
│   │   ├── schema.yml
│   │   └── examples/
│   ├── mapping-guide.md               # CSV mapping documentation
│   ├── sql-transformation-guide.md    # SQL transformation patterns
│   ├── transformation-approaches.md   # Comparison: CSV vs SQL vs Rules
│   └── SQL_IMPLEMENTATION.md          # SQL feature summary
│
├── src/                               # Source code
│   ├── __init__.py
│   ├── main.py                        # CLI entry point
│   │
│   ├── config/                        # Configuration loading
│   │   ├── __init__.py
│   │   └── loader.py                  # YAML config parser
│   │
│   ├── connectors/                    # Data source/sink adapters
│   │   ├── __init__.py
│   │   ├── base.py                    # Abstract Source & Sink
│   │   └── postgres.py                # PostgreSQL implementation
│   │
│   ├── metadata/                      # Metadata handling
│   ├── models/                        # Data models
│   │
│   ├── pipelines/                     # ELT orchestration
│   │   ├── __init__.py
│   │   ├── orchestrator.py            # Pipeline execution engine
│   │   ├── transformations.py         # Rule-based transforms
│   │   ├── mapping.py                 # CSV column mapping
│   │   ├── sql_transform.py           # SQL transformation engine
│   │   └── validation.py              # Data quality validation
│   │
│   ├── runners/                       # Execution runners
│   ├── services/                      # Business logic services
│   └── utils/                         # Utility functions
│
├── tests/                             # Test suite
│   └── unit/
│       └── (test files)
│
└── jobs/                             # Complete workflow examples
    │
    ├── README.md                      # Master guide
    ├── STRUCTURE.md                   # Organization guide
    │
    ├── 01_customer_migration_simple/  # Beginner example
    │   ├── README.md
    │   ├── pipeline.yml
    │   └── transformations.sql
    │
    ├── 02_customer_migration_full/    # Intermediate example
    │   ├── README.md
    │   ├── pipeline.yml
    │   ├── mappings.csv
    │   └── transformations.sql
    │
    └── 03_orders_incremental/         # Advanced example
        ├── README.md
        ├── pipeline.yml
        ├── mappings.csv
        └── transformations.sql
```

## Key Sections

### `src/` - Source Code

- **Single responsibility**: Each module has one clear purpose
- **Config layer**: `config/loader.py` parses YAML configurations
- **Connector layer**: `connectors/` handles data movement (extract/load)
- **Transformation layer**: `pipelines/` handles transformations and validation
- **Execution layer**: `main.py` orchestrates everything

### `docs/` - Documentation

- **Architecture**: System design and patterns
- **Guides**: Developer guides, getting started, runbooks
- **Features**: Mapping, SQL transformation, validation documentation

### `jobs/` - Workflows

- **Workflow-based**: Each directory = one complete job
- **Self-contained**: Everything needed to run in one place
- **Progressive**: 01 (simple) → 02 (complete) → 03 (advanced)

## Data Flow Through System

```
jobs/01_/pipeline.yml
    ↓
config/loader.py (parse YAML)
    ↓
src/main.py (CLI entry)
    ↓
pipelines/orchestrator.py
    ├─ connectors/postgres.py (Extract)
    │   └─ Source.extract() → raw data
    │
    ├─ connectors/postgres.py (Load)
    │   └─ Sink.load() → landing table
    │
    ├─ pipelines/mapping.py (Transform)
    │   └─ CSV mappings applied
    │
    ├─ pipelines/sql_transform.py (Transform)
    │   └─ SQL logic executed on DB
    │
    ├─ pipelines/transformations.py (Transform)
    │   └─ Rule-based transformations
    │
    └─ pipelines/validation.py (Validate)
        └─ Quality checks run
            ↓
            report.json (execution summary)
```

## File Organization Philosophy

### Source Code (`src/`)
- **Language**: Python
- **Structure**: By responsibility (config, connectors, pipelines)
- **Purpose**: Reusable, production-ready code
- **Complexity**: Abstractions, classes, interfaces

### Jobs (`jobs/`)
- **Language**: Mixed (YAML, SQL, CSV)
- **Structure**: By workflow/job (01_, 02_, 03_)
- **Purpose**: Learning and reuse
- **Complexity**: Simple to advanced progression

### This separation means:

✅ Engineers maintain clean source code
✅ Users have complete workflow examples
✅ Easy to adapt examples for production use
✅ Clear learning path from simple to advanced
✅ One job per directory = clear ownership

## Typical Workflow

### Step 1: Understand Requirements
```bash
cd jobs/
ls -la                                  # See available jobs
cat 01_customer_migration_simple/README.md  # Understand job
```

### Step 2: Adapt to Your Data
```bash
cp -r jobs/01_customer_migration_simple/ my_job/
# Edit my_job/pipeline.yml with your database details
# Edit my_job/transformations.sql with your business logic
```

### Step 3: Run Pipeline
```bash
# Option A: Using full path
python src/main.py my_job/pipeline.yml -v --report report.json

# Option B: Using job name (auto-resolved)
python src/main.py 01_customer_migration_simple -v --report report.json
```

### Step 4: Validate Results
```bash
# Check report.json
# Verify data in target tables
# Troubleshoot if needed
```

## Extension Points

### Add New Connector
```python
src/connectors/mysql.py
# Implement MySQLSource & MySQLSink
# Register in ConnectorRegistry
```

### Add New Transformation Type
```python
src/pipelines/transformations.py
# Add new TransformationRule subclass
# Update Transformer.transform_row()
```

### Add New Validation Rule
```python
src/pipelines/validation.py
# Add new ValidationRule subclass
# Update Validator.from_config()
```

### Add New Job Workflow
```
jobs/NN_new_workflow/
├── README.md
├── pipeline.yml
├── mappings.csv (optional)
└── transformations.sql
```

## Summary

| Component | Location | Purpose |
|-----------|----------|---------|
| **Config** | `src/config/` | Parse pipeline YAML |
| **Connectors** | `src/connectors/` | Extract/Load data |
| **Pipelines** | `src/pipelines/` | Transform/Validate data |
| **Main** | `src/main.py` | CLI entry point |
| **Docs** | `docs/` | Project documentation |
| **Examples** | `examples/` | Complete workflow samples |

This structure supports:
- **Scalability**: Easy to add new components
- **Maintainability**: Clear organization
- **Learning**: Progressive examples
- **Production**: Real-world patterns
