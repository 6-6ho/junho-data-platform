-- 10. Generator Settings Table for Admin Dashboard

CREATE TABLE IF NOT EXISTS shop_generator_settings (
    id SERIAL PRIMARY KEY,
    mode VARCHAR(20) DEFAULT 'normal', -- normal, sale, test
    base_tps INT DEFAULT 100,
    chaos_mode BOOLEAN DEFAULT FALSE,
    category_bias VARCHAR(50), -- e.g. 'electronics', 'fashion', or NULL for no bias
    user_persona_bias VARCHAR(50), -- e.g. 'heavy_buyer', or NULL for no bias
    expires_at TIMESTAMP NULL, -- If set, settings revert to defaults after this time
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Insert default row if empty
INSERT INTO shop_generator_settings (id, mode, base_tps, chaos_mode, category_bias, user_persona_bias, expires_at)
SELECT 1, 'normal', 100, FALSE, NULL, NULL, NULL
WHERE NOT EXISTS (SELECT 1 FROM shop_generator_settings WHERE id = 1);
