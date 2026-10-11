{{
    config(
        materialized='table'
    )
}}

SELECT
    unnest(results)                 AS r,
    generate_subscripts(results, 1) AS row_number,
    country,
    _feed_type,
    updated
FROM read_json_auto(
    '{{ uri("bronze") }}/snapshot_date={{ var("snapshot_date") }}/*.json',
    union_by_name = true
)
WHERE _feed_type IS NOT NULL
  AND results    IS NOT NULL
  AND country    IS NOT NULL
