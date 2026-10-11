// Bronze (raw): BigLake external table over NDJSON in the bronze bucket (created by Terraform),
// Hive-partitioned by snapshot_date. Declared so the silver model can ref() it.
declare({
  schema: "bronze_apple_rss",
  name: "top_charts",
  description: "Apple RSS top-free/top-paid charts, one file per country and feed, as returned by the API.",
});
