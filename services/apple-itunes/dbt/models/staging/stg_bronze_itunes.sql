{{
    config(
        materialized='table'
    )
}}

SELECT
    unnest(results)                            AS r,
    generate_subscripts(results, 1)            AS row_number,
    _feed_type,
    country,
    _ingested_at,
    CAST('{{ var("snapshot_date") }}' AS DATE) AS snapshot_date
FROM read_json_auto(
    '{{ uri("bronze") }}/snapshot_date={{ var("snapshot_date") }}/*.json',
    union_by_name = true,
    columns = {
        '_feed_type':   'VARCHAR',
        '_ingested_at': 'VARCHAR',
        'country':      'VARCHAR',
        'results':      'STRUCT(
            trackId BIGINT,
            trackName VARCHAR,
            artistId BIGINT,
            artistName VARCHAR,
            sellerName VARCHAR,
            bundleId VARCHAR,
            primaryGenreId BIGINT,
            primaryGenreName VARCHAR,
            genres VARCHAR[],
            price DOUBLE,
            formattedPrice VARCHAR,
            currency VARCHAR,
            version VARCHAR,
            minimumOsVersion VARCHAR,
            fileSizeBytes BIGINT,
            contentAdvisoryRating VARCHAR,
            releaseDate VARCHAR,
            currentVersionReleaseDate VARCHAR,
            averageUserRating DOUBLE,
            userRatingCount BIGINT,
            averageUserRatingForCurrentVersion DOUBLE,
            userRatingCountForCurrentVersion BIGINT,
            description VARCHAR,
            releaseNotes VARCHAR,
            artworkUrl100 VARCHAR,
            trackViewUrl VARCHAR,
            languageCodesISO2A VARCHAR[],
            advisories VARCHAR[],
            screenshotUrls VARCHAR[],
            ipadScreenshotUrls VARCHAR[]
        )[]'
    }
)
WHERE _feed_type IS NOT NULL
  AND results    IS NOT NULL
  AND country    IS NOT NULL
