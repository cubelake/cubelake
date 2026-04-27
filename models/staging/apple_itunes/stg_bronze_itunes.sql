{{
    config(
        materialized='table'
    )
}}

SELECT
    unnest(results)                 AS r,
    generate_subscripts(results, 1) AS row_number,
    _feed_type,
    country
FROM read_json_auto(
    'azure://bronze/appstore_itunes/snapshot_date={{ var("snapshot_date") }}/*.json',
    union_by_name = true,
    columns = {
        '_feed_type': 'VARCHAR',
        'country':    'VARCHAR',
        'results':    'STRUCT(trackId BIGINT, trackName VARCHAR, artistName VARCHAR, bundleId VARCHAR, primaryGenreName VARCHAR, genres JSON, price DOUBLE, formattedPrice VARCHAR, averageUserRating DOUBLE, userRatingCount BIGINT, releaseDate VARCHAR, currentVersionReleaseDate VARCHAR, version VARCHAR, trackViewUrl VARCHAR, artworkUrl512 VARCHAR)[]'
    }
)
WHERE _feed_type IS NOT NULL
  AND results    IS NOT NULL
  AND country    IS NOT NULL
