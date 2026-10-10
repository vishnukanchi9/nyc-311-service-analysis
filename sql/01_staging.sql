-- 01_staging.sql
-- Build a typed, cleaned table of 2025 service requests from the raw Parquet extract.
-- Every data-quality rule is applied as a flag rather than a silent delete so the
-- impact of each rule can be measured in 02_data_quality.sql.

CREATE OR REPLACE TABLE stg_requests AS
WITH typed AS (
    SELECT
        CAST(unique_key AS BIGINT)                                  AS request_id,
        CAST(created_date AS TIMESTAMP)                             AS created_at,
        CAST(closed_date AS TIMESTAMP)                              AS closed_at,
        UPPER(TRIM(agency))                                         AS agency,
        TRIM(complaint_type)                                        AS complaint_type,
        TRIM(descriptor)                                            AS descriptor,
        TRIM(status)                                                AS status,
        -- keep only well-formed 5-digit ZIPs
        CASE WHEN regexp_full_match(TRIM(incident_zip), '\d{5}')
             THEN TRIM(incident_zip) END                            AS zip,
        NULLIF(UPPER(TRIM(borough)), 'UNSPECIFIED')                 AS borough,
        UPPER(TRIM(community_board))                                AS community_board,
        UPPER(COALESCE(open_data_channel_type, 'UNKNOWN'))          AS channel,
        CAST(latitude AS DOUBLE)                                    AS latitude,
        CAST(longitude AS DOUBLE)                                   AS longitude
    FROM read_parquet('data/raw/*.parquet')
),
-- Some complaint types appear under two spellings ("Plumbing" vs "PLUMBING",
-- "Elevator" vs "ELEVATOR"). Map every variant to its most common spelling.
canonical AS (
    SELECT lower(complaint_type) AS complaint_key, MODE(complaint_type) AS complaint_group
    FROM typed
    GROUP BY 1
)
SELECT
    typed.*,
    canonical.complaint_group,
    date_diff('minute', created_at, closed_at) / 60.0               AS resolution_hours,
    closed_at IS NOT NULL                                           AS is_closed,
    -- Data-quality flags
    closed_at < created_at                                          AS dq_closed_before_created,
    closed_at = created_at                                          AS dq_zero_duration,
    date_diff('day', created_at, closed_at) > 365                   AS dq_over_one_year,
    borough IS NULL                                                 AS dq_missing_borough,
    -- Valid community boards look like "05 BROOKLYN"; anything else (e.g. "0 Unspecified")
    -- cannot be mapped to a district.
    NOT regexp_full_match(community_board, '\d{2} (MANHATTAN|BRONX|BROOKLYN|QUEENS|STATEN ISLAND)')
                                                                    AS dq_invalid_community_board
FROM typed
JOIN canonical ON lower(typed.complaint_type) = canonical.complaint_key
WHERE created_at >= TIMESTAMP '2025-01-01'
  AND created_at <  TIMESTAMP '2026-01-01';

-- Analysis view: drops only records that are impossible (closed before they were
-- created). Zero-duration closures and closures after more than a year are real
-- outcomes (auto-closures, long HPD/DOB cases), so they stay in.
CREATE OR REPLACE VIEW requests AS
SELECT *
FROM stg_requests
WHERE NOT COALESCE(dq_closed_before_created, FALSE);
