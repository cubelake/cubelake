# ingestion-apple-itunes

> Async ingestion library for the Apple iTunes Lookup API — part of the [Cubelake](https://github.com/Cubelake/cubelake) data platform.

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)
![httpx](https://img.shields.io/badge/httpx-async-30638E)
![License](https://img.shields.io/badge/License-MIT-green)

Given a batch of app IDs grouped by country/feed, fetches full app metadata from Apple's iTunes Lookup API. It does not discover app IDs itself and does not touch storage — both are the caller's responsibility.

---

## What it does

- The caller (the `bronze_itunes_lookup_daily` Airflow DAG in [`appstore-dags`](https://github.com/Cubelake/appstore-dags)) reads app IDs that charted on a given day from the **silver RSS** Parquet output (queried via DuckDB) and passes them in as `dict[str, list[str]]`, keyed by preset key (e.g. `{"us_top_free": ["284882215", "544007664"]}`).
- This package batches all IDs for a preset key into a single comma-separated lookup request via [`appstore-core`](https://github.com/Cubelake/appstore-core)'s `AppleItunesUrlBuilder`:
  ```
  https://itunes.apple.com/lookup?id=284882215,544007664&country=us
  ```
- Preset keys with an empty ID list are skipped.
- The raw JSON response (which itself contains a `results` array of all requested apps) is returned as-is per preset key — per-app flattening happens downstream in the silver dbt transform, not in this package.

## Usage

There's no CLI — it's a library meant to be driven by an orchestrator:

```python
import asyncio
from ingestion_apple_itunes.ingestor import Ingestor

results = asyncio.run(Ingestor().collect({"us_top_free": ["284882215", "544007664"]}))
# [{"preset_key": "us_top_free", "url": "...", "feed": {"resultCount": 2, "results": [...]}}]
```

In production, the calling DAG wraps each result with `appstore-core`'s `BronzeRow` and writes it as newline-delimited JSON to `bronze/appstore_itunes/snapshot_date=YYYY-MM-DD/` in ADLS.

## Key modules

| File | Responsibility |
|---|---|
| `ingestion_apple_itunes/ingestor.py` | `Ingestor(BaseIngestor)` — `collect(app_ids_by_key)`, `normalize()` |
| `ingestion_apple_itunes/url_factory.py` | `UrlFactory` — builds one lookup URL per preset key, skipping empty ID lists |

## Configuration

No environment variables are read by this package. Country is derived by splitting the preset key on `_` (`"us_top_free".split("_")[0]` → `"us"`) — there's an implicit assumption that preset keys always start with `"{country}_"`. Batching/timeout/retry behavior comes from `appstore-core`'s `IngestionConfig` (`batch_size=10`, `timeout_seconds=15.0`, `max_retries=2`) and is not currently overridable from here.

## Install & test

Part of the `cubelake` uv workspace — not published standalone.

```bash
# from the workspace root
uv sync --all-packages
uv run pytest ingestion-apple-itunes/tests/ -v
```

`tests/test_url_creation.py` covers URL construction (single vs. multi-ID lookups) and preset-key-to-URL mapping, including the empty-ID-list skip behavior.

## Known limitations

- No tests for `Ingestor.collect()` itself (HTTP fetch, retries) — only URL construction is covered.
- No handling specific to iTunes API rate limiting beyond the generic retry/backoff in `appstore-core`.
- Country parsing from the preset key isn't validated against the RSS package's supported-country list.

## License

[MIT](LICENSE)
