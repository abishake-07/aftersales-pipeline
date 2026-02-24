-- ════════════════════════════════════════════════════════════
-- Sample Athena Queries — BMW Aftersales Pipeline
-- ════════════════════════════════════════════════════════════
-- Run these against the bmw_aftersales.tickets_enriched view.
-- ════════════════════════════════════════════════════════════


-- ── KPI 1: Daily ticket volume (last 30 days) ─────────────
SELECT
    DATE(created_at)            AS ticket_date,
    COUNT(*)                    AS ticket_count
FROM bmw_aftersales.tickets_enriched
WHERE created_at >= current_timestamp - INTERVAL '30' DAY
GROUP BY DATE(created_at)
ORDER BY ticket_date;


-- ── KPI 2: Severity distribution ───────────────────────────
SELECT
    severity,
    COUNT(*)                                    AS cnt,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) AS pct
FROM bmw_aftersales.tickets_enriched
GROUP BY severity
ORDER BY severity;


-- ── KPI 3: SLA breach rate (overall & by severity) ────────
SELECT
    severity,
    COUNT(*)                                            AS total,
    SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END)      AS breached,
    ROUND(SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END)
          * 100.0 / COUNT(*), 1)                        AS breach_pct
FROM bmw_aftersales.tickets_enriched
GROUP BY severity
ORDER BY severity;


-- ── KPI 4: Average resolution time by severity ────────────
SELECT
    severity,
    ROUND(AVG(resolution_hours), 1)     AS avg_res_hrs,
    ROUND(APPROX_PERCENTILE(resolution_hours, 0.5), 1) AS median_res_hrs,
    ROUND(APPROX_PERCENTILE(resolution_hours, 0.95), 1) AS p95_res_hrs
FROM bmw_aftersales.tickets_enriched
WHERE resolution_hours IS NOT NULL
GROUP BY severity
ORDER BY severity;


-- ── KPI 5: Tickets by market ──────────────────────────────
SELECT
    market,
    COUNT(*)    AS tickets,
    SUM(CASE WHEN sla_breached THEN 1 ELSE 0 END) AS sla_breaches
FROM bmw_aftersales.tickets_enriched
GROUP BY market
ORDER BY tickets DESC;


-- ── KPI 6: Top 5 issue categories ─────────────────────────
SELECT
    category,
    COUNT(*) AS cnt
FROM bmw_aftersales.tickets_enriched
GROUP BY category
ORDER BY cnt DESC
LIMIT 5;


-- ── KPI 7: Open tickets by age bucket ─────────────────────
SELECT
    CASE
        WHEN days_open <= 1  THEN '0-1 day'
        WHEN days_open <= 3  THEN '2-3 days'
        WHEN days_open <= 7  THEN '4-7 days'
        ELSE '7+ days'
    END AS age_bucket,
    COUNT(*) AS open_tickets
FROM bmw_aftersales.tickets_enriched
WHERE status NOT IN ('Resolved', 'Closed')
GROUP BY 1
ORDER BY MIN(days_open);


-- ── KPI 8: Market × Severity heatmap data ─────────────────
SELECT
    market,
    severity,
    COUNT(*) AS cnt
FROM bmw_aftersales.tickets_enriched
GROUP BY market, severity
ORDER BY market, severity;


-- ── KPI 9: Weekly trend — open vs closed ───────────────────
SELECT
    DATE_TRUNC('week', created_at)   AS week_start,
    status,
    COUNT(*)                         AS cnt
FROM bmw_aftersales.tickets_enriched
GROUP BY 1, status
ORDER BY week_start, status;


-- ── KPI 10: P1 tickets still open (action list) ───────────
SELECT
    ticket_id,
    created_at,
    category,
    market,
    dealer_id,
    model_series,
    days_open
FROM bmw_aftersales.tickets_enriched
WHERE severity = 'P1'
  AND status NOT IN ('Resolved', 'Closed')
ORDER BY created_at ASC;
