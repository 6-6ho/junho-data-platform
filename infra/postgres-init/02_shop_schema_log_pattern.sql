-- Shop Analytics Bench Schema

-- 1. Real-time Metrics (Key-Value style for fast access)
-- Used for: Active Users, Total Revenue (Today), Total Orders
CREATE TABLE IF NOT EXISTS shop_realtime_metrics (
    metric_name VARCHAR(50) PRIMARY KEY,
    metric_value DECIMAL(14, 2), -- Supports large revenue numbers
    last_updated TIMESTAMP DEFAULT NOW()
);

-- 2. Hourly Sales Aggregation (for Bar Charts/Trends)
-- Used for: "Revenue by Category" chart
CREATE TABLE IF NOT EXISTS shop_hourly_sales (
    window_start TIMESTAMP,
    window_end TIMESTAMP,
    category VARCHAR(50),
    total_revenue DECIMAL(14, 2),
    order_count INT,
    avg_order_value DECIMAL(10, 2),
    PRIMARY KEY (window_start, category)
);

-- 3. Funnel Statistics (Session Based)
-- Used for: Funnel Chart (View -> Cart -> Purchase)
CREATE TABLE IF NOT EXISTS shop_funnel_stats (
    window_start TIMESTAMP,
    total_sessions INT,
    view_count INT,
    cart_count INT,
    purchase_count INT,
    conversion_rate DECIMAL(5, 2),
    PRIMARY KEY (window_start)
);

-- 4. Brand Performance
-- Used for: "Top Brands" ranking
CREATE TABLE IF NOT EXISTS shop_brand_stats (
    window_start TIMESTAMP,
    brand_name VARCHAR(50),
    total_revenue DECIMAL(14, 2),
    order_count INT,
    PRIMARY KEY (window_start, brand_name)
);

-- Initial Seed Data (Optional, to avoid empty dashboard before first stream)
INSERT INTO shop_realtime_metrics (metric_name, metric_value) VALUES 
('active_users_5m', 0),
('total_revenue_today', 0),
('total_orders_today', 0)
ON CONFLICT (metric_name) DO NOTHING;
