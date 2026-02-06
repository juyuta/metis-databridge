-- Customer Data Transformation Pipeline
-- Transforms raw landing data to business-ready analytics table
-- Using CTEs and SQL for declarative transformations

-- @step: validate_source_data
-- @description: Check data quality and row counts in source
SELECT
    COUNT(*) as total_rows,
    COUNT(DISTINCT customer_id) as unique_customers,
    COUNT(*) FILTER (WHERE customer_id IS NULL) as null_customer_ids,
    COUNT(*) FILTER (WHERE email IS NULL) as null_emails
FROM ${SOURCE_TABLE}
WHERE 1=1;

-- @step: clean_customer_data
-- @description: Deduplicate and clean raw customer records
-- @depends_on: validate_source_data
CREATE TEMP TABLE temp_customers_clean AS
WITH ranked_customers AS (
    SELECT
        customer_id,
        customer_name,
        TRIM(LOWER(email)) as email,
        phone,
        created_at,
        updated_at,
        is_active,
        account_balance,
        country,
        region_id,
        ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY updated_at DESC) as rn
    FROM ${SOURCE_TABLE}
    WHERE customer_id IS NOT NULL
)
SELECT
    customer_id,
    customer_name,
    email,
    phone,
    created_at::DATE as created_date,
    updated_at::TIMESTAMP as last_modified,
    is_active,
    account_balance::NUMERIC(12,2) as balance,
    COALESCE(country, 'US') as country,
    region_id
FROM ranked_customers
WHERE rn = 1
    AND customer_id IS NOT NULL;

-- @step: enrich_customer_data
-- @description: Add calculated fields and business logic
-- @depends_on: clean_customer_data
CREATE TEMP TABLE temp_customers_enriched AS
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
    -- Calculate customer tenure in days
    CURRENT_DATE - created_date as tenure_days,
    -- Calculate customer age tier
    CASE
        WHEN tenure_days < 30 THEN 'NEW'
        WHEN tenure_days < 365 THEN 'ACTIVE'
        WHEN tenure_days < 730 THEN 'MATURE'
        ELSE 'VETERAN'
    END as customer_tier,
    -- Segment by balance
    CASE
        WHEN balance < 100 THEN 'LOW_VALUE'
        WHEN balance < 1000 THEN 'MEDIUM_VALUE'
        WHEN balance < 10000 THEN 'HIGH_VALUE'
        ELSE 'PREMIUM'
    END as value_segment,
    -- Flag high-value customers
    CASE WHEN balance >= 10000 AND is_active THEN true ELSE false END as is_vip,
    -- Current timestamp
    CURRENT_TIMESTAMP as processed_at
FROM temp_customers_clean;

-- @step: create_analytics_table
-- @description: Create final analytics-ready customer dimension
-- @depends_on: enrich_customer_data
-- @final: true
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

-- @step: populate_analytics_table
-- @description: Load transformed data into final table
-- @depends_on: create_analytics_table
INSERT INTO ${TARGET_TABLE}
SELECT * FROM temp_customers_enriched
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
-- @depends_on: populate_analytics_table
CREATE INDEX IF NOT EXISTS idx_customer_email ON ${TARGET_TABLE}(email);
CREATE INDEX IF NOT EXISTS idx_customer_country ON ${TARGET_TABLE}(country);
CREATE INDEX IF NOT EXISTS idx_customer_tier ON ${TARGET_TABLE}(customer_tier);
CREATE INDEX IF NOT EXISTS idx_customer_is_active ON ${TARGET_TABLE}(is_active);

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
    SUM(balance) as total_balance,
    AVG(balance) as avg_balance,
    MIN(balance) as min_balance,
    MAX(balance) as max_balance,
    MAX(processed_at) as last_processed
FROM ${TARGET_TABLE};
