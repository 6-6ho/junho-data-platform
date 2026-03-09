-- Dynamic Theme: DBSCAN clustering by daily high-time proximity
-- Runs daily via Airflow, parallel to manual theme system

CREATE TABLE IF NOT EXISTS dynamic_theme_cluster (
    cluster_id SERIAL PRIMARY KEY,
    created_date DATE NOT NULL,
    coin_count INTEGER NOT NULL,
    strength_score DOUBLE PRECISION NOT NULL,
    avg_high_time TIMESTAMPTZ NOT NULL,
    time_spread_minutes DOUBLE PRECISION NOT NULL,
    avg_high_change_pct DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_dtc_date ON dynamic_theme_cluster(created_date DESC);

CREATE TABLE IF NOT EXISTS dynamic_theme_member (
    cluster_id INTEGER REFERENCES dynamic_theme_cluster(cluster_id) ON DELETE CASCADE,
    symbol TEXT NOT NULL,
    high_time TIMESTAMPTZ NOT NULL,
    high_price DOUBLE PRECISION NOT NULL,
    high_change_pct DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (cluster_id, symbol)
);
