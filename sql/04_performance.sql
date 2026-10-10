-- 04_performance.sql
-- How quickly are requests resolved, and where are the bottlenecks?
-- Resolution times are heavily right-skewed, so medians and percentiles are
-- reported instead of means.

-- name: agency_performance
-- EDC is excluded: its helicopter-noise complaints are bulk-closed months later,
-- so its "resolution time" measures a batch process, not case handling.
SELECT
    agency,
    COUNT(*)                                                        AS requests,
    ROUND(100.0 * AVG(CASE WHEN is_closed THEN 1 ELSE 0 END), 1)    AS pct_closed,
    ROUND(MEDIAN(resolution_hours), 1)                              AS median_hours,
    ROUND(quantile_cont(resolution_hours, 0.9), 1)                  AS p90_hours,
    ROUND(100.0 * AVG(CASE WHEN resolution_hours <= 24 THEN 1 ELSE 0 END)
          FILTER (WHERE is_closed), 1)                              AS pct_within_1_day,
    ROUND(100.0 * AVG(CASE WHEN resolution_hours <= 24 * 7 THEN 1 ELSE 0 END)
          FILTER (WHERE is_closed), 1)                              AS pct_within_7_days
FROM requests
WHERE agency <> 'EDC'
GROUP BY agency
HAVING COUNT(*) >= 5000
ORDER BY requests DESC;

-- name: complaint_performance
-- Top 25 complaint types by volume with their resolution profile.
SELECT
    complaint_group,
    MODE(agency)                                                    AS primary_agency,
    COUNT(*)                                                        AS requests,
    ROUND(100.0 * AVG(CASE WHEN is_closed THEN 1 ELSE 0 END), 1)    AS pct_closed,
    ROUND(MEDIAN(resolution_hours), 1)                              AS median_hours,
    ROUND(quantile_cont(resolution_hours, 0.9), 1)                  AS p90_hours
FROM requests
GROUP BY complaint_group
ORDER BY requests DESC
LIMIT 25;

-- name: open_backlog
-- Requests created in 2025 that are still open at extract time.
SELECT
    agency,
    complaint_group,
    COUNT(*)                                                        AS still_open,
    MIN(created_at)::DATE                                           AS oldest_open
FROM stg_requests
WHERE NOT is_closed
GROUP BY 1, 2
ORDER BY still_open DESC
LIMIT 15;

-- name: monthly_median_resolution
SELECT
    date_trunc('month', created_at)::DATE                           AS month,
    agency,
    ROUND(MEDIAN(resolution_hours), 1)                              AS median_hours,
    COUNT(*)                                                        AS requests
FROM requests
WHERE agency IN ('NYPD', 'HPD', 'DSNY', 'DOT', 'DEP', 'DOB', 'DPR')
GROUP BY 1, 2
ORDER BY 2, 1;

