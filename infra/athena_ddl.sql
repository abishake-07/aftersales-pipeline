-- ════════════════════════════════════════════════════════════
-- Athena DDL — BMW Aftersales Support Tickets
-- ════════════════════════════════════════════════════════════
-- Run these statements in the Athena Query Editor.
-- Replace <ACCOUNT_ID> below with the AWS_ACCOUNT_ID value from your .env file.
-- (Athena SQL doesn't support variables — this is a one-time manual find-replace.)
-- ════════════════════════════════════════════════════════════


-- ── 1. Create database ─────────────────────────────────────

CREATE DATABASE IF NOT EXISTS bmw_aftersales;


-- ── 2. Raw table (JSON-Lines in S3) ────────────────────────

CREATE EXTERNAL TABLE IF NOT EXISTS bmw_aftersales.tickets_raw (
    ticket_id       STRING,
    created_at      STRING,
    updated_at      STRING,
    resolved_at     STRING,
    severity        STRING,
    status          STRING,
    category        STRING,
    channel         STRING,
    market          STRING,
    dealer_id       STRING,
    customer_id     STRING,
    vin_last6       STRING,
    model_series    STRING,
    model_year      INT,
    sla_breached    BOOLEAN
)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
LOCATION 's3://bmw-aftersales-raw-<ACCOUNT_ID>/tickets/'
TBLPROPERTIES ('has_encrypted_data'='false');


-- ── 3. Curated table (Parquet, partitioned by market) ──────

CREATE EXTERNAL TABLE IF NOT EXISTS bmw_aftersales.tickets (
    ticket_id       STRING,
    created_at      TIMESTAMP,
    updated_at      TIMESTAMP,
    resolved_at     TIMESTAMP,
    severity        STRING,
    status          STRING,
    category        STRING,
    channel         STRING,
    dealer_id       STRING,
    customer_id     STRING,
    vin_last6       STRING,
    model_series    STRING,
    model_year      INT,
    sla_breached    BOOLEAN
)
PARTITIONED BY (market STRING)
STORED AS PARQUET
LOCATION 's3://bmw-aftersales-curated-<ACCOUNT_ID>/tickets/'
TBLPROPERTIES (
    'parquet.compression'='SNAPPY',
    'has_encrypted_data'='false'
);

-- After uploading Parquet files, load partitions:
MSCK REPAIR TABLE bmw_aftersales.tickets;


-- ── 4. Create a view with computed columns ─────────────────

CREATE OR REPLACE VIEW bmw_aftersales.tickets_enriched AS
SELECT
    *,
    date_diff('hour', created_at, COALESCE(resolved_at, current_timestamp))
        AS hours_since_created,
    CASE
        WHEN resolved_at IS NOT NULL
        THEN date_diff('hour', created_at, resolved_at)
        ELSE NULL
    END AS resolution_hours,
    CASE
        WHEN resolved_at IS NULL
        THEN date_diff('day', created_at, current_timestamp)
        ELSE NULL
    END AS days_open
FROM bmw_aftersales.tickets;
