-- Dynamic Theme v2: correlation-based clustering
-- daily_correlation stores pairwise Pearson correlations from 5m returns
-- Additional columns on existing cluster/member tables for correlation data

CREATE TABLE IF NOT EXISTS daily_correlation (
    date DATE NOT NULL,
    symbol_a VARCHAR(20) NOT NULL,
    symbol_b VARCHAR(20) NOT NULL,
    correlation DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (date, symbol_a, symbol_b)
);
CREATE INDEX IF NOT EXISTS idx_daily_corr_date ON daily_correlation(date);

-- Add correlation columns to existing tables
ALTER TABLE dynamic_theme_cluster
  ADD COLUMN IF NOT EXISTS lead_symbol VARCHAR(20),
  ADD COLUMN IF NOT EXISTS lead_change_pct DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS avg_correlation DOUBLE PRECISION;

ALTER TABLE dynamic_theme_member
  ADD COLUMN IF NOT EXISTS daily_change_pct DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS correlation_to_lead DOUBLE PRECISION;
