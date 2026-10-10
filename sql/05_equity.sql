-- 05_equity.sql
-- Do some parts of the city get slower service?
--
-- Raw comparisons are misleading: boroughs file very different mixes of
-- complaints (e.g. Queens files more slow-to-resolve street-condition requests,
-- Manhattan more fast-closing noise complaints). To compare like with like, each
-- closed request is benchmarked against the citywide median resolution time for
-- its complaint type. Citywide, ~50% of requests beat their benchmark by
-- construction; an area well below 50% is slower than expected for its mix.

-- name: benchmarks
CREATE OR REPLACE TEMP TABLE benchmarked AS
WITH bench AS (
    SELECT complaint_group, MEDIAN(resolution_hours) AS bench_hours, COUNT(*) AS n
    FROM requests
    WHERE is_closed
    GROUP BY complaint_group
    HAVING COUNT(*) >= 500              -- only types with a stable benchmark
)
SELECT
    r.*,
    b.bench_hours,
    -- ties at the median (common for auto-closures) count as half a win so the
    -- citywide rate stays at 50%
    CASE WHEN r.resolution_hours < b.bench_hours THEN 1.0
         WHEN r.resolution_hours = b.bench_hours THEN 0.5
         ELSE 0.0 END                                               AS beat_benchmark
FROM requests r
JOIN bench b USING (complaint_group)
WHERE r.is_closed;

-- name: borough_equity
SELECT
    borough,
    COUNT(*)                                                        AS closed_requests,
    ROUND(MEDIAN(resolution_hours), 1)                              AS raw_median_hours,
    ROUND(100.0 * AVG(beat_benchmark), 1)                           AS pct_faster_than_citywide
FROM benchmarked
WHERE borough IS NOT NULL
GROUP BY borough
ORDER BY pct_faster_than_citywide;

-- name: district_equity
-- Community-district level view (59 districts). Joint parks / airports and
-- other non-residential "districts" (numbered 26+) are dropped. Borough is taken
-- from the district name: a few districts straddle borough lines (e.g. Marble
-- Hill is in Manhattan but served by Bronx CD 8).
SELECT
    community_board,
    SUBSTR(community_board, 4)                                      AS borough,
    COUNT(*)                                                        AS closed_requests,
    ROUND(MEDIAN(resolution_hours), 1)                              AS raw_median_hours,
    AVG(beat_benchmark)                                             AS share_faster
FROM benchmarked
WHERE NOT dq_invalid_community_board
  AND TRY_CAST(LEFT(community_board, 2) AS INT) < 26
GROUP BY community_board
HAVING COUNT(*) >= 1000
ORDER BY share_faster;

-- name: district_equity_by_agency
-- Is the gap driven by one agency or all of them?
SELECT
    agency,
    borough,
    COUNT(*)                                                        AS closed_requests,
    ROUND(100.0 * AVG(beat_benchmark), 1)                           AS pct_faster_than_citywide
FROM benchmarked
WHERE borough IS NOT NULL
  AND agency IN ('NYPD', 'HPD', 'DSNY', 'DOT', 'DEP', 'DOB', 'DPR')
GROUP BY agency, borough
ORDER BY agency, borough;

-- name: slowest_district_drilldown
-- Which complaint types make the slowest district slow? Excess hours = actual
-- median minus the citywide benchmark for the same complaint type.
WITH worst AS (
    SELECT community_board
    FROM benchmarked
    WHERE NOT dq_invalid_community_board
      AND TRY_CAST(LEFT(community_board, 2) AS INT) < 26
    GROUP BY 1
    HAVING COUNT(*) >= 1000
    ORDER BY AVG(beat_benchmark)
    LIMIT 1
)
SELECT
    community_board,
    complaint_group,
    agency,
    COUNT(*)                                                        AS closed_requests,
    ROUND(MEDIAN(resolution_hours), 1)                              AS district_median_hours,
    ROUND(ANY_VALUE(bench_hours), 1)                                AS citywide_median_hours,
    ROUND(100.0 * AVG(beat_benchmark), 1)                           AS pct_faster_than_citywide
FROM benchmarked
WHERE community_board IN (SELECT community_board FROM worst)
GROUP BY 1, 2, 3
ORDER BY closed_requests DESC
LIMIT 10;

-- name: borough_equity_robustness
-- Sensitivity checks: does the borough ranking survive (a) dropping zero-duration
-- auto-closures and (b) removing NYPD entirely?
SELECT
    borough,
    ROUND(100.0 * AVG(beat_benchmark), 1)                                        AS all_requests,
    ROUND(100.0 * AVG(beat_benchmark) FILTER (WHERE NOT dq_zero_duration), 1)    AS excl_zero_duration,
    ROUND(100.0 * AVG(beat_benchmark) FILTER (WHERE agency <> 'NYPD'), 1)        AS excl_nypd
FROM benchmarked
WHERE borough IS NOT NULL
GROUP BY borough
ORDER BY all_requests;

-- name: nypd_core_types_by_borough
-- NYPD's three highest-volume complaint types, borough by borough.
SELECT
    complaint_group,
    borough,
    COUNT(*)                                                        AS closed_requests,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY complaint_group), 1)
                                                                    AS pct_of_citywide,
    ROUND(MEDIAN(resolution_hours), 2)                              AS median_hours
FROM benchmarked
WHERE agency = 'NYPD'
  AND complaint_group IN ('Noise - Residential', 'Illegal Parking', 'Blocked Driveway')
  AND borough IS NOT NULL
GROUP BY 1, 2
ORDER BY 1, median_hours DESC;
