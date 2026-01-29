-- Shop Analytics Bench Schema (Log Pattern for Speed Layer)

-- 1. Real-time Metrics LOG
CREATE TABLE IF NOT EXISTS shop_realtime_metrics_log (
    metric_name VARCHAR(50),
    metric_value DECIMAL(14, 2),
    last_updated TIMESTAMP DEFAULT NOW()
);
-- View: Get latest value for each metric
-- CREATE OR REPLACE VIEW shop_realtime_metrics AS 
-- SELECT DISTINCT ON (metric_name) * FROM shop_realtime_metrics_log ORDER BY metric_name, last_updated DESC;
-- (Actually, we can just query the log table with ORDER BY LIMIT 1 in dashboard for speed, or create this view)

CREATE OR REPLACE VIEW shop_realtime_metrics AS
SELECT DISTINCT ON (metric_name) metric_name, metric_value, last_updated
FROM shop_realtime_metrics_log
ORDER BY metric_name, last_updated DESC;


-- 2. Hourly Sales LOG
CREATE TABLE IF NOT EXISTS shop_hourly_sales_log (
    window_start TIMESTAMP,
    window_end TIMESTAMP,
    category VARCHAR(50),
    total_revenue DECIMAL(14, 2),
    order_count INT,
    avg_order_value DECIMAL(10, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- View: Get latest update for each window/category
CREATE OR REPLACE VIEW shop_hourly_sales AS
SELECT DISTINCT ON (window_start, category) *
FROM shop_hourly_sales_log
ORDER BY window_start, category, created_at DESC;


-- 3. Funnel Statistics LOG
CREATE TABLE IF NOT EXISTS shop_funnel_stats_log (
    window_start TIMESTAMP,
    total_sessions INT,
    view_count INT,
    cart_count INT,
    purchase_count INT,
    conversion_rate DECIMAL(5, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE OR REPLACE VIEW shop_funnel_stats AS
SELECT DISTINCT ON (window_start) *
FROM shop_funnel_stats_log
ORDER BY window_start, created_at DESC;


-- 4. Brand Performance LOG
CREATE TABLE IF NOT EXISTS shop_brand_stats_log (
    window_start TIMESTAMP,
    brand_name VARCHAR(50),
    total_revenue DECIMAL(14, 2),
    order_count INT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE OR REPLACE VIEW shop_brand_stats AS
SELECT DISTINCT ON (window_start, brand_name) *
FROM shop_brand_stats_log
ORDER BY window_start, brand_name, created_at DESC;


-- Seed Data (Optional)
INSERT INTO shop_realtime_metrics_log (metric_name, metric_value) VALUES 
('active_users_5m', 0),
('total_revenue_today', 0),
('total_orders_today', 0);
