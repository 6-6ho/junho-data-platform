-- User RFM Analysis Mart
CREATE TABLE IF NOT EXISTS mart_user_rfm (
    user_id VARCHAR(50) PRIMARY KEY,
    recency_days INT,
    frequency INT,
    monetary NUMERIC,
    r_score INT,
    f_score INT,
    m_score INT,
    rfm_group VARCHAR(20),  -- VIP, Potential, Churned, etc.
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Product Affinity Analysis Mart
-- Stores association rules: If people buy A (antecedent), they buy B (consequent)
CREATE TABLE IF NOT EXISTS mart_product_association (
    rule_id SERIAL PRIMARY KEY,
    antecedents VARCHAR(255), -- Product IDs (comma separated or JSON)
    consequents VARCHAR(255),
    confidence DOUBLE PRECISION,
    lift DOUBLE PRECISION,
    support DOUBLE PRECISION,
    calculated_at DATE DEFAULT CURRENT_DATE
);

-- Index for fast lookup by antecedent (product page recommendation)
CREATE INDEX IF NOT EXISTS idx_affinity_antecedents ON mart_product_association(antecedents);
