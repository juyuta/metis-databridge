-- Simple Customer Transformation
-- Basic transformation with minimal steps

-- @step: deduplicate
-- @description: Keep only latest version of each customer
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
-- @description: Load deduplicated data to target table
-- @depends_on: deduplicate
-- @final: true
INSERT INTO ${TARGET_TABLE}
SELECT
    customer_id,
    customer_name,
    LOWER(TRIM(email)) as email,
    phone,
    created_at::DATE as created_date,
    updated_at::TIMESTAMP as last_modified,
    is_active,
    account_balance::NUMERIC(12,2) as balance,
    COALESCE(country, 'US') as country,
    region_id,
    CURRENT_TIMESTAMP as processed_at
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
