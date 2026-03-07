-- 3-Tier Migration: [Large]/[Small] → [High]/[Mid]/[Small]
-- Run manually on laptop Postgres (jdp-postgres-1) AFTER stopping Spark jobs
-- This file is idempotent: safe to re-run if [Large] rows no longer exist

DO $$
BEGIN
    -- Skip if no [Large] rows exist (already migrated)
    IF NOT EXISTS (SELECT 1 FROM movers_latest WHERE status LIKE '[Large]%' LIMIT 1) THEN
        RAISE NOTICE '3-tier migration already applied, skipping';
        RETURN;
    END IF;

    -- Backup
    CREATE TABLE IF NOT EXISTS movers_latest_backup_3tier AS SELECT * FROM movers_latest;

    -- Reclassify + deduplicate into temp table
    CREATE TEMP TABLE movers_clean AS
    SELECT DISTINCT ON (type, new_status, symbol, event_time)
        type, symbol, new_status AS status, "window", event_time,
        change_pct_window, change_pct_24h, vol_ratio, updated_at
    FROM (
        SELECT *,
            CASE
                WHEN "window" = '5m' AND change_pct_window >= 11.0 THEN '[High] Rise'
                WHEN "window" = '5m' AND change_pct_window >= 7.0  THEN '[Mid] Rise'
                WHEN "window" = '10m' AND change_pct_window >= 10.0 THEN '[High] Rise'
                WHEN "window" = '10m' AND change_pct_window >= 7.0  THEN '[Mid] Rise'
                ELSE status  -- [Small] Rise stays as-is
            END AS new_status
        FROM movers_latest WHERE type = 'rise'
    ) sub
    ORDER BY type, new_status, symbol, event_time, change_pct_window DESC;

    DELETE FROM movers_latest WHERE type = 'rise';

    INSERT INTO movers_latest (type, symbol, status, "window", event_time,
        change_pct_window, change_pct_24h, vol_ratio, updated_at)
    SELECT * FROM movers_clean;

    DROP TABLE movers_clean;

    RAISE NOTICE '3-tier migration completed successfully';
END $$;
