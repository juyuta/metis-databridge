-- Simple Customer Transformation
-- Basic deduplication and type casting

-- @step: deduplicate_customers
-- @description: Keep only the latest version of each customer
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

-- @step: load_to_target
-- @description: Load deduplicated data to target table with type casting
-- @depends_on: deduplicate_customers
-- @final: true
INSERT INTO ${TARGET_TABLE} (
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
    processed_at
)
SELECT
    customer_id::INTEGER,
    TRIM(customer_name)::VARCHAR(255),
    LOWER(TRIM(email))::VARCHAR(255),
    phone::VARCHAR(20),
    created_at::DATE,
    updated_at::TIMESTAMP,
    is_active::BOOLEAN,
    COALESCE(account_balance::NUMERIC(12,2), 0.00),
    COALESCE(country, 'US')::VARCHAR(10),
    region_id::INTEGER,
    CURRENT_TIMESTAMP
FROM customers_dedup
ON CONFLICT (customer_id) DO UPDATE SET
    customer_name = EXCLUDED.customer_name,
    email = EXCLUDED.email,
    phone = EXCLUDED.phone,
    is_active = EXCLUDED.is_active,
    balance = EXCLUDED.balance,
    country = EXCLUDED.country,
    region_id = EXCLUDED.region_id,
    last_modified = EXCLUDED.last_modified,
    processed_at = EXCLUDED.processed_at;
