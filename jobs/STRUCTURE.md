# Examples Directory Structure & Organization

## Workflow-Based Organization

Metis DataBridge examples are organized by **workflow/job** rather than by file type. Each directory represents a complete, self-contained data migration or ETL job.

```
examples/
├── README.md                              # Master guide for all examples
│
├── 01_customer_migration_simple/          # Beginner: Basic ELT
│   ├── README.md                         # Workflow documentation
│   ├── pipeline.yml                      # Configuration
│   └── transformations.sql               # SQL transformation steps
│
├── 02_customer_migration_full/            # Intermediate: All features
│   ├── README.md                         # Workflow documentation
│   ├── pipeline.yml                      # Configuration
│   ├── mappings.csv                      # Column metadata
│   └── transformations.sql               # SQL transformation steps
│
└── 03_orders_incremental/                 # Advanced: Production patterns
    ├── README.md                         # Workflow documentation
    ├── pipeline.yml                      # Configuration
    ├── mappings.csv                      # Column metadata
    └── transformations.sql               # SQL transformation steps
```

## Why This Structure?

### ✅ Advantages

1. **Self-Contained**: Each job has everything needed to run
   - No missing files
   - Easy to copy and adapt
   - Clear dependencies

2. **Easy Discovery**: Each directory represents one job
   - Users can easily find examples
   - Clear progression (01 → 02 → 03)
   - README explains what each does

3. **Realistic**: Mirrors real-world ETL workflows
   - Data engineers think in terms of "jobs" or "pipelines"
   - Not in terms of "all CSVs here, all SQLs there"

4. **Maintainability**: Changes are grouped by workflow
   - Update one job? Update its directory
   - No searching across multiple locations

5. **Clarity**: Purpose is immediately obvious
   - Directory name tells you what it does
   - Complexity level in name (01, 02, 03)
   - README explains the approach

## File Organization Pattern

Each workflow follows this pattern:

```
NN_workflow_name/
├── README.md              # What this workflow does, how to run it
├── pipeline.yml           # Main configuration (required)
├── mappings.csv          # Column mapping metadata (optional)
└── transformations.sql   # SQL transformation logic (optional)
```

### Naming Convention

**Directories:**
- Prefix: `NN_` (01_, 02_, 03_) for ordering
- Name: Snake_case describing the workflow
- Example: `01_customer_migration_simple`

**Files:**
- `pipeline.yml` - Always named consistently
- `mappings.csv` - If column mapping needed
- `transformations.sql` - If SQL transformation needed
- `README.md` - Always present

## How Users Navigate

### For Beginners
1. Read `examples/README.md`
2. Open `examples/01_customer_migration_simple/README.md`
3. Run `pipeline.yml`
4. Understand `transformations.sql`

### For Intermediate Users
1. Review `02_customer_migration_full/README.md`
2. Study `mappings.csv` format
3. Examine complex SQL in `transformations.sql`
4. Copy and customize

### For Advanced Users
1. Jump to `03_orders_incremental/README.md`
2. Learn fact/dimension patterns
3. Study window functions and aggregations
4. Implement incremental load logic

## Comparison Matrix

| Aspect | Example 1 | Example 2 | Example 3 |
|--------|-----------|-----------|-----------|
| **Complexity** | Beginner | Intermediate | Advanced |
| **Job Type** | Simple Migration | Full-Featured | Incremental Load |
| **Components** | SQL only | SQL + Mapping | SQL + Mapping |
| **Run Time** | ~5s | ~10s | ~15s |
| **Lines of SQL** | 40 | 150 | 250 |
| **Best For** | Learning | Production | Data Warehouse |

## Adding New Examples

To add a new workflow:

1. Create directory: `examples/NN_workflow_description/`
   - Use next number in sequence
   - Use descriptive snake_case name

2. Create files:
   - `README.md` - Explain the workflow
   - `pipeline.yml` - Configuration
   - `mappings.csv` - If needed
   - `transformations.sql` - If needed

3. Document in master `examples/README.md`
   - Add to directory listing
   - Add to feature matrix
   - Describe learning outcomes

## Real-World Job Examples

This structure supports real-world scenarios:

### Scenario: E-commerce Data Warehouse

```
examples/
├── 01_products_sync/
├── 02_customers_scd/          # Slowly Changing Dimension
├── 03_orders_incremental/     # ← Already in examples!
├── 04_inventory_snapshot/     # Periodic snapshot
├── 05_order_items_facts/
└── 06_returns_dimension/
```

Each is a separate, schedulable job that teams run independently.

### Scenario: Data Lake Ingestion

```
examples/
├── 01_raw_api_to_landing/
├── 02_raw_database_to_landing/
├── 03_landing_to_silver/      # Cleaning
├── 04_silver_to_gold/         # Aggregation
└── 05_gold_to_marts/          # Business layer
```

Each layer is a separate job in the pipeline.

## Integration with Version Control

When using Git:

```bash
# View all workflows
ls examples/

# Work on one workflow
cd examples/02_customer_migration_full/
git add .
git commit -m "Update customer migration job"

# Review changes for specific workflow
git diff examples/02_customer_migration_full/
```

## Key Principles

1. **One Job = One Directory**
   - Self-contained and complete
   - Easy to understand and modify

2. **Consistent Structure**
   - Every job has the same file organization
   - Users know where to look

3. **Progressive Complexity**
   - Start simple (01), progress to advanced (03)
   - Clear learning path

4. **Self-Documenting**
   - Directory names explain purpose
   - README files explain approach
   - Code is commented

5. **Production-Ready**
   - Real patterns (dedup, incremental, fact/dimension)
   - Performance considerations
   - Error handling

## See Also

- [Examples README](README.md) - Guide to running examples
- [SQL Transformation Guide](../docs/sql-transformation-guide.md)
- [Mapping Guide](../docs/mapping-guide.md)
