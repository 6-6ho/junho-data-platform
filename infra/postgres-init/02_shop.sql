-- Database for Shopping Analytics
-- Tables will be created by Spark Jobs via JDBC (mode=overwrite)

-- CREATE DATABASE shop_analytics; (This runs in transaction block, might fail in init script if not careful, but usually fine in docker-entrypoint)
-- Actually, Postgres Initdb runs scripts against the requested DB (POSTGRES_DB=app).
-- To create another DB, we need to explicitly connect to template1 or just run CREATE DATABASE.
-- In docker-entrypoint-initdb.d, scripts run as superuser.
-- Note: You cannot run CREATE DATABASE inside a transaction block.
-- The docker image wrapper handles this?
-- Usually, we include:

CREATE DATABASE shop_analytics;
