-- Customer Data Transformation Pipeline
-- Comprehensive example with deduplication, cleaning, and enrichment

-- @step: validate_source
-- @description: Check data quality and row counts in source
SELECT
    COUNT(*) as total_rows,
    COUNT(DISTINCT customer_id) as unique_customers,
    COUNT(*) FILTER (WHERE customer_id IS NULL) as null_ids,
    COUNT(*) FILTER (WHERE email IS NULL) as null_emails
FROM ${SOURCE_TABLE};

-- @step: deduplicate
-- @description: Keep only latest version of each customer
-- @depends_on: validate_source
CREATE TEMP TABLE customers_dedup AS
SELECT DISTINCT ON (customer_id)
    customer_id,
    customer_name,
    email,
    phone,
    created_at,
    updated_at,
    is_active,
    account_balance,
    country,
    region_id
FROM ${SOURCE_TABLE}
WHERE customer_id IS NOT NULL
ORDER BY customer_id, updated_at DESC;

-- @step: clean_data
-- @description: Standardize and clean customer records
-- @depends_on: deduplicate
CREATE TEMP TABLE customers_clean AS
SELECT
    customer_id,
    TRIM(customer_name) as customer_name,
    LOWER(TRIM(email)) as email,
    phone,
    created_at::DATE as created_date,
    updated_at::TIMESTAMP as last_modified,
    CASE
        WHEN is_active IN ('Y', 'yes', '1', true) THEN true
        ELSE false
    END as is_active,
    account_balance::NUMERIC(12,2) as balance,
    COALESCE(country, 'US') as country,
    region_id
FROM customers_dedup;

-- @step: enrich_data
-- @description: Add calculated fields for analytics
-- @depends_on: clean_data
CREATE TEMP TABLE customers_enriched AS
SELECT
    customer_id,
    customer_name,
    email,
    phone,
    created_date,
    last_modified,
    is_active,
    balance,
    country,
    region_id,
    -- Calculate tenure
    CURRENT_DATE - created_date as tenure_days,
    -- Classify by tenure
    CASE
        WHEN CURRENT_DATE - created_date < 30 THEN 'NEW'
        WHEN CURRENT_DATE - created_date < 365 THEN 'ACTIVE'
        WHEN CURRENT_DATE - created_date < 730 THEN 'MATURE'
        ELSE 'VETERAN'
    END as customer_tier,
    -- Segment by balance
    CASE
        WHEN balance < 100 THEN 'LOW_VALUE'
        WHEN balance < 1000 THEN 'MEDIUM_VALUE'
        WHEN balance < 10000 THEN 'HIGH_VALUE'
        ELSE 'PREMIUM'
    END as value_segment,
    -- VIP flag
    CASE WHEN balance >= 10000 AND is_active THEN true ELSE false END as is_vip,
    CURRENT_TIMESTAMP as processed_at
FROM customers_clean;

-- @step: create_target_table
-- @description: Create final analytics-ready customer table
-- @depends_on: enrich_data
CREATE TABLE IF NOT EXISTS ${TARGET_TABLE} (
    customer_id INTEGER PRIMARY KEY,
    customer_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    created_date DATE NOT NULL,
    last_modified TIMESTAMP,
    is_active BOOLEAN NOT NULL,
    balance NUMERIC(12,2),
    country VARCHAR(10),
    region_id INTEGER,
    tenure_days INTEGER,
    customer_tier VARCHAR(20),
    value_segment VARCHAR(20),
    is_vip BOOLEAN,
    processed_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- @step: populate_target
-- @description: Load transformed data into final table
-- @depends_on: create_target_table
INSERT INTO ${TARGET_TABLE}
SELECT
    customer_id,
    customer_name,
    email,
    phone,
    created_date,
    last_modified,
    is_active,
    balance,
    country,
    region_id,
    tenure_days,
    customer_tier,
    value_segment,
    is_vip,
    processed_at
FROM customers_enriched
ON CONFLICT (customer_id) DO UPDATE SET
    customer_name = EXCLUDED.customer_name,
    email = EXCLUDED.email,
    phone = EXCLUDED.phone,
    is_active = EXCLUDED.is_active,
    balance = EXCLUDED.balance,
    country = EXCLUDED.country,
    region_id = EXCLUDED.region_id,
    tenure_days = EXCLUDED.tenure_days,
    customer_tier = EXCLUDED.customer_tier,
    value_segment = EXCLUDED.value_segment,
    is_vip = EXCLUDED.is_vip,
    last_modified = EXCLUDED.last_modified,
    processed_at = EXCLUDED.processed_at;

-- @step: create_indexes
-- @description: Create indexes for query performance
-- @depends_on: populate_target
CREATE INDEX IF NOT EXISTS idx_customer_email ON ${TARGET_TABLE}(email);
CREATE INDEX IF NOT EXISTS idx_customer_country ON ${TARGET_TABLE}(country);
CREATE INDEX IF NOT EXISTS idx_customer_tier ON ${TARGET_TABLE}(customer_tier);
CREATE INDEX IF NOT EXISTS idx_customer_is_active ON ${TARGET_TABLE}(is_active);
CREATE INDEX IF NOT EXISTS idx_customer_is_vip ON ${TARGET_TABLE}(is_vip);

-- @step: gather_statistics
-- @description: Update table statistics for query planner
-- @depends_on: create_indexes
ANALYZE ${TARGET_TABLE};

-- @step: validate_output
-- @description: Final validation of transformed data
-- @depends_on: gather_statistics
SELECT
    COUNT(*) as total_records,
    COUNT(DISTINCT customer_id) as unique_customers,
    COUNT(*) FILTER (WHERE is_active) as active_customers,
    COUNT(*) FILTER (WHERE is_vip) as vip_customers,
    COUNT(DISTINCT country) as distinct_countries,
    SUM(balance) as total_balance,
    AVG(balance) as avg_balance,
    MIN(balance) as min_balance,
    MAX(balance) as max_balance,
    MAX(processed_at) as last_processed
FROM ${TARGET_TABLE};
