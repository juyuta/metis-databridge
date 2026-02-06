-- Orders Incremental Load Pipeline
-- Demonstrates advanced patterns: fact/dimension, aggregation, incremental load

-- @step: validate_source
-- @description: Check source data quality
SELECT
    COUNT(*) as total_orders,
    COUNT(DISTINCT order_id) as unique_orders,
    COUNT(DISTINCT customer_id) as unique_customers,
    MIN(order_date) as earliest_order,
    MAX(order_date) as latest_order,
    COUNT(*) FILTER (WHERE order_amount IS NULL) as null_amounts
FROM ${SOURCE_TABLE};

-- @step: deduplicate_orders
-- @description: Remove duplicate orders, keep latest version
CREATE TEMP TABLE orders_dedup AS
SELECT DISTINCT ON (order_id)
    order_id,
    order_date,
    customer_id,
    product_id,
    quantity,
    unit_price,
    total_amount,
    order_status,
    created_at,
    updated_at
FROM ${SOURCE_TABLE}
WHERE order_id IS NOT NULL
ORDER BY order_id, updated_at DESC;

-- @step: clean_orders
-- @description: Standardize and type cast order data
-- @depends_on: deduplicate_orders
CREATE TEMP TABLE orders_clean AS
SELECT
    order_id::INTEGER,
    order_date::DATE,
    customer_id::INTEGER,
    product_id::INTEGER,
    quantity::INTEGER,
    unit_price::NUMERIC(12,2),
    (quantity * unit_price)::NUMERIC(12,2) as calculated_amount,
    COALESCE(total_amount::NUMERIC(12,2), quantity * unit_price) as order_amount,
    UPPER(TRIM(order_status))::VARCHAR(20) as status,
    created_at::TIMESTAMP,
    updated_at::TIMESTAMP
FROM orders_dedup;

-- @step: enrich_with_order_metrics
-- @description: Add calculated fields and order metrics
-- @depends_on: clean_orders
CREATE TEMP TABLE orders_enriched AS
SELECT
    order_id,
    order_date,
    customer_id,
    product_id,
    quantity,
    unit_price,
    order_amount,
    status,
    created_at,
    updated_at,
    -- Order recency rank (most recent = 1)
    ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date DESC) as recency_rank,
    -- Running total per customer
    SUM(order_amount) OVER (PARTITION BY customer_id ORDER BY order_date) as customer_running_total,
    -- Days since order
    CURRENT_DATE - order_date as days_ago,
    -- Order size classification
    CASE
        WHEN order_amount < 50 THEN 'SMALL'
        WHEN order_amount < 200 THEN 'MEDIUM'
        WHEN order_amount < 1000 THEN 'LARGE'
        ELSE 'XLARGE'
    END as order_size,
    CURRENT_TIMESTAMP as processed_at
FROM orders_clean;

-- @step: create_fact_table
-- @description: Create fact_orders table for incremental load
-- @depends_on: enrich_with_order_metrics
CREATE TABLE IF NOT EXISTS fact_orders (
    order_id INTEGER PRIMARY KEY,
    order_date DATE NOT NULL,
    customer_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER,
    unit_price NUMERIC(12,2),
    order_amount NUMERIC(12,2),
    status VARCHAR(20),
    order_size VARCHAR(20),
    days_ago INTEGER,
    processed_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- @step: incremental_load_orders
-- @description: Upsert orders (insert new, update modified)
-- @depends_on: create_fact_table
-- @final: true
INSERT INTO fact_orders (
    order_id, order_date, customer_id, product_id,
    quantity, unit_price, order_amount, status,
    order_size, days_ago, processed_at
)
SELECT
    order_id, order_date, customer_id, product_id,
    quantity, unit_price, order_amount, status,
    order_size, days_ago, processed_at
FROM orders_enriched
ON CONFLICT (order_id) DO UPDATE SET
    order_amount = EXCLUDED.order_amount,
    status = EXCLUDED.status,
    order_size = EXCLUDED.order_size,
    days_ago = EXCLUDED.days_ago,
    processed_at = EXCLUDED.processed_at,
    updated_at = CURRENT_TIMESTAMP;

-- @step: create_customer_metrics
-- @description: Aggregate order metrics by customer
-- @depends_on: incremental_load_orders
CREATE TABLE IF NOT EXISTS customer_order_metrics AS
SELECT
    customer_id,
    COUNT(*) as order_count,
    SUM(order_amount) as total_spent,
    AVG(order_amount) as avg_order_value,
    MIN(order_date) as first_order_date,
    MAX(order_date) as last_order_date,
    MAX(order_date) - MIN(order_date) as customer_tenure_days,
    COUNT(*) FILTER (WHERE status IN ('COMPLETED', 'SHIPPED')) as completed_orders,
    COUNT(*) FILTER (WHERE status = 'CANCELLED') as cancelled_orders,
    CURRENT_TIMESTAMP as metric_timestamp
FROM fact_orders
GROUP BY customer_id;

-- @step: create_indexes
-- @description: Create indexes for query performance
-- @depends_on: incremental_load_orders
CREATE INDEX IF NOT EXISTS idx_orders_customer ON fact_orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_product ON fact_orders(product_id);
CREATE INDEX IF NOT EXISTS idx_orders_date ON fact_orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_status ON fact_orders(status);

-- @step: gather_statistics
-- @description: Update table statistics
-- @depends_on: create_indexes
ANALYZE fact_orders;
ANALYZE customer_order_metrics;

-- @step: validate_output
-- @description: Validate transformed orders
-- @depends_on: gather_statistics
SELECT
    COUNT(*) as fact_orders_count,
    COUNT(DISTINCT customer_id) as distinct_customers,
    COUNT(DISTINCT product_id) as distinct_products,
    COUNT(*) FILTER (WHERE status IN ('COMPLETED', 'SHIPPED')) as completed,
    COUNT(*) FILTER (WHERE status = 'CANCELLED') as cancelled,
    SUM(order_amount) as total_revenue,
    AVG(order_amount) as avg_order_value,
    MIN(order_amount) as min_order_value,
    MAX(order_amount) as max_order_value,
    MAX(processed_at) as last_processed
FROM fact_orders;
