-- 03_demand.sql
-- What are New Yorkers asking for, when, and through which channel?

-- name: monthly_volume
SELECT
    date_trunc('month', created_at)::DATE                           AS month,
    COUNT(*)                                                        AS requests
FROM requests
GROUP BY 1
ORDER BY 1;

-- name: top_complaints
SELECT
    complaint_group,
    COUNT(*)                                                        AS requests,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2)              AS pct_of_total,
    ROUND(100.0 * SUM(COUNT(*)) OVER (ORDER BY COUNT(*) DESC
          ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW)
          / SUM(COUNT(*)) OVER (), 1)                               AS cumulative_pct
FROM requests
GROUP BY complaint_group
ORDER BY requests DESC
LIMIT 15;

-- name: complaint_type_count
SELECT COUNT(DISTINCT complaint_group) AS complaint_types FROM requests;

-- name: seasonality_top_complaints
-- Monthly volume for the biggest complaint types, indexed to their own annual
-- average (100 = an average month) so seasonal shape is comparable across types.
WITH top AS (
    SELECT complaint_group FROM requests
    GROUP BY 1 ORDER BY COUNT(*) DESC LIMIT 8
),
monthly AS (
    SELECT complaint_group, month(created_at) AS month_num, COUNT(*) AS requests
    FROM requests
    WHERE complaint_group IN (SELECT complaint_group FROM top)
    GROUP BY 1, 2
)
SELECT
    complaint_group,
    month_num,
    requests,
    ROUND(100.0 * requests / AVG(requests) OVER (PARTITION BY complaint_group), 1) AS seasonal_index
FROM monthly
ORDER BY complaint_group, month_num;

-- name: hour_by_weekday
SELECT
    dayofweek(created_at)                                           AS weekday_num,   -- 0 = Sunday
    dayname(created_at)                                             AS weekday,
    hour(created_at)                                                AS hour,
    COUNT(*)                                                        AS requests
FROM requests
-- Many agencies stamp back-office entries at exactly midnight; exclude them
-- so the heatmap reflects when residents actually report problems.
WHERE strftime(created_at, '%H:%M:%S') <> '00:00:00'
GROUP BY 1, 2, 3
ORDER BY 1, 3;

-- name: channel_mix
SELECT
    channel,
    COUNT(*)                                                        AS requests,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)              AS pct
FROM requests
GROUP BY channel
ORDER BY requests DESC;

-- name: borough_volume
SELECT
    borough,
    COUNT(*)                                                        AS requests,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)              AS pct
FROM requests
WHERE borough IS NOT NULL
GROUP BY borough
ORDER BY requests DESC;
