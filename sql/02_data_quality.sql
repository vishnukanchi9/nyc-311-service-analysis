-- 02_data_quality.sql
-- Quantify each data-quality issue before any analysis. Output feeds the
-- "Data quality" section of the report.

-- name: dq_summary
SELECT
    COUNT(*)                                                        AS total_requests,
    COUNT(DISTINCT request_id)                                      AS distinct_request_ids,
    SUM(CASE WHEN NOT is_closed THEN 1 ELSE 0 END)                  AS still_open,
    SUM(CASE WHEN dq_closed_before_created THEN 1 ELSE 0 END)       AS closed_before_created,
    SUM(CASE WHEN dq_zero_duration THEN 1 ELSE 0 END)               AS zero_duration,
    SUM(CASE WHEN dq_over_one_year THEN 1 ELSE 0 END)               AS open_over_one_year,
    SUM(CASE WHEN dq_missing_borough THEN 1 ELSE 0 END)             AS missing_borough,
    SUM(CASE WHEN zip IS NULL THEN 1 ELSE 0 END)                    AS missing_or_bad_zip,
    SUM(CASE WHEN dq_invalid_community_board THEN 1 ELSE 0 END)     AS invalid_community_board,
    SUM(CASE WHEN latitude IS NULL THEN 1 ELSE 0 END)               AS missing_coordinates
FROM stg_requests;

-- name: dq_closed_before_created_by_agency
-- Negative durations are concentrated in a few agencies, which points to a
-- system/process issue rather than random entry error.
SELECT
    agency,
    COUNT(*)                                                        AS requests,
    SUM(CASE WHEN dq_closed_before_created THEN 1 ELSE 0 END)       AS closed_before_created,
    ROUND(100.0 * SUM(CASE WHEN dq_closed_before_created THEN 1 ELSE 0 END) / COUNT(*), 2)
                                                                    AS pct_closed_before_created,
    ROUND(100.0 * SUM(CASE WHEN dq_zero_duration THEN 1 ELSE 0 END) / COUNT(*), 2)
                                                                    AS pct_zero_duration
FROM stg_requests
GROUP BY agency
HAVING COUNT(*) >= 1000
ORDER BY pct_closed_before_created DESC;
