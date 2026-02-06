# Metis DataBridge

**Metis DataBridge** is a metadata-driven data migration and ETL framework designed to build highly configurable pipelines with minimal hardcoding logic for each data source or transformation. The framework prioritizes *configuration over code*, enabling repeatable, auditable, and scalable data movement between systems.

Metis starts small by design: a flexible execution core with a limited set of common connectors (e.g. PostgreSQL, flat files), while remaining extensible for future sources, sinks, and transformation patterns.

---

## The Problem We Solve

### Enterprise ETL is Broken for Modern Data Teams

Traditional tools (Informatica, Talend, etc.) create real friction:

| Pain Point | Reality |
|-----------|---------|
| **Lock-in** | Tight coupling to proprietary platforms, licenses, and UI-driven workflows |
| **Transparency** | Logic hidden behind UI abstractions; hard to review, audit, or understand |
| **Portability** | Migration logic stuck in the tool; impossible to version control or reuse |
| **Overhead** | Significant setup cost even for simple source → target moves |
| **Iteration** | Changes require UI manipulation; can't use git workflows or peer review |
| **Team Friction** | Analysts create spreadsheets, engineers write custom Python; fragmented solutions |

**The result:** Expensive tools, vendor lock-in, and data teams doing workarounds instead of real work.

---

## Our Approach: Configuration as Code

Metis inverts the traditional paradigm:

```
Traditional ETL:  Code → Config (after the fact)
Metis approach:   Config → Code (code is the config)
```

### Why This Matters

1. **Git-friendly** - Pipelines live in version control, enable code review, branching, and blame
2. **Transparent** - No black boxes; see exactly what happens at each step
3. **Lightweight** - Start a pipeline in minutes, not weeks
4. **Extensible** - Add new connectors without touching core logic
5. **Democratic** - Non-engineers can understand and modify pipelines (YAML + SQL)

### Design Philosophy

- **Fewer connectors, richer configuration** - Quality over breadth
- **ELT over ETL** - Leverage modern database power for transformations
- **Metadata-driven** - Mappings, validations, and rules in simple files
- **Minimal dependencies** - Only what you need: psycopg, PyYAML, pandas

---

## What Does Success Look Like?

A data migration should be **repeatable, auditable, and fast**:

✅ **Repeatability** - Run the same pipeline 100 times, get the same result  
✅ **Auditability** - Every transformation is visible in git history  
✅ **Speed** - SQL on the database, not Python in memory (20-30x faster)  
✅ **Simplicity** - No UI wizards; just YAML + SQL files you understand  

---

## Quick Start

```bash
# 1. Set up test databases
createdb legacy_db
createdb analytics_db

# 2. Run a complete job
python src/main.py 01_customer_migration_simple -v

# 3. That's it!
# - Extracted 50K rows from legacy_db
# - Loaded to landing table in analytics_db
# - Applied transformations (deduplication)
# - Validated data quality
# - Generated report
```

One command. End-to-end. Repeatable.

---

## Core Capabilities

### 📋 Configuration-Driven Pipelines
Define jobs in simple YAML:
```yaml
source: legacy_db.customers
sink: analytics_db.customers_clean
mapping_file: mappings.csv
sql_transform_file: transformations.sql
validations:
  - row_count
  - null_check: customer_id
```

### 📝 Three Transformation Layers (Pick Your Abstraction)
- **CSV Mappings:** Column renames, type casting (non-technical)
- **SQL Transforms:** Multi-step, server-side, 20-30x faster
- **Python Rules:** Complex logic (fallback for edge cases)

### ✅ Built-In Validation
- Row count checks
- Null/duplicate detection
- Custom validation rules
- Execution reports (JSON)

### 🔌 Extensible Connectors
- PostgreSQL (production)
- MySQL, Snowflake, BigQuery (planned)
- CSV, Parquet (planned)
- Add custom connectors easily

### 📊 Execution Transparency
Every pipeline generates:
- Detailed logs (what happened)
- Execution metrics (rows, duration, status)
- Validation results (data quality)
- JSON reports (programmatic)

---

## Vision & Roadmap

### Phase 1: Core Framework ✅ (Complete)
- [x] ELT orchestration engine
- [x] PostgreSQL source & sink
- [x] YAML configuration
- [x] SQL + CSV transformations
- [x] Validation framework
- [x] CLI interface

### Phase 2: Real-World Ready 🔄 (In Progress)
- [ ] Unit & integration tests
- [ ] Error recovery & retry logic
- [ ] File-based connectors (CSV, Parquet)
- [ ] Production deployment guide

### Phase 3: Enterprise Features (Planned)
- [ ] Change Data Capture (CDC) for incremental loads
- [ ] Multiple cloud connectors (Snowflake, BigQuery, Redshift)
- [ ] Data lineage tracking
- [ ] Advanced validation rules
- [ ] Performance optimization guide

### Phase 4: Ecosystem (Long-term)
- [ ] Spark execution mode (100B+ rows)
- [ ] Airflow integration
- [ ] REST API for job execution
- [ ] Web UI for pipeline management
- [ ] AI-augmented features (auto-mapping, auto-validation)

---

## Why Metis Exists

We built Metis because:

1. **Enterprise tools are overkill** for data migration work - they add cost and complexity
2. **Modern databases are powerful** - SQL can do what used to require ETL platforms
3. **Teams want version control** - Git workflows should apply to data pipelines
4. **Configuration > Code** - Non-engineers should understand pipeline logic
5. **Simple tools win** - Fewer features, better focus, easier to master

We're not trying to replace Informatica or Talend. We're solving the 80% of migration work that doesn't need enterprise complexity.

---

## Who Should Use Metis?

✅ **Good fit:**
- Data engineers building reusable pipelines
- Teams doing database migrations
- Organizations prioritizing transparency & git workflows
- Teams needing to scale from 1M to 1B rows
- Anyone who wants to understand their data pipelines

❌ **Not ideal (yet):**
- Real-time streaming (Kafka, event-based)
- Complex AI/ML feature engineering
- Distributed processing across 1000s of nodes (future: Spark support)
- Multi-cloud orchestration (future: Airflow integration)

---

## Contributing & Community

### Design First
Open an issue before major features. We discuss architecture before code.

### Trunk-Based Development
Small, frequent PRs to `main`. Continuous integration.

### Clear Standards
- Python 3.10+
- Type-checked code (Pylance)
- Tests for all features (coming soon)
- Documentation for user-facing changes

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for technical design.

---

## Next Steps

1. **Read the docs:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) covers technical details
2. **Run examples:** `python src/main.py 01_customer_migration_simple`
3. **Start small:** Pick one data migration job, build it with Metis
4. **Contribute:** Help us build the next phase

---

## License

GNU General Public License v3.0 - See [LICENSE](LICENSE)

---

## Made for Data Engineers

Metis is built by data engineers for data engineers. We believe:

- **Simplicity wins** - The best tool is the one you actually understand
- **Code review applies to data** - Pipelines should be in git, with diffs and reviews
- **Modern databases are powerful** - Stop moving data just to transform it
- **Configuration > Platform** - YAML > UI wizards every time

**Let's build better data pipelines together.** 🚀
