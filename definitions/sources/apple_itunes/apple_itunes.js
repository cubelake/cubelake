// Bronze (raw): BigLake external table over NDJSON in the bronze bucket (created by Terraform),
// Hive-partitioned by snapshot_date. Declared so the silver model can ref() it.
declare({
  schema: "bronze_apple_itunes",
  name: "lookup",
  description: "iTunes lookup responses for every app charted by apple-rss, one file per country and feed.",
});
