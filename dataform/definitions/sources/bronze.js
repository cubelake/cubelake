// Raw zone: BigLake external tables over NDJSON in the bronze bucket (created by Terraform),
// Hive-partitioned by snapshot_date. Declared here so silver models can ref() them.
declare({
  schema: "bronze_apple_rss",
  name: "top_charts",
  description: "Apple RSS top-free/top-paid charts, one file per country and feed, as returned by the API.",
});

declare({
  schema: "bronze_apple_itunes",
  name: "lookup",
  description: "iTunes lookup responses for every app charted by apple-rss, one file per country and feed.",
});
