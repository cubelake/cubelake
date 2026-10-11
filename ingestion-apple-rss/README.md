# ingestion-apple-rss

> Async ingestion library for Apple's public RSS "top apps" marketing feed — part of the [Cubelake](https://github.com/Cubelake/cubelake) data platform.

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)
![httpx](https://img.shields.io/badge/httpx-async-30638E)
![License](https://img.shields.io/badge/License-MIT-green)

Fetches Apple's `top-free` / `top-paid` app charts for every supported country and normalizes them into flat, in-memory records. It does not talk to storage — the caller (the `bronze_top_daily` Airflow DAG in [`appstore-dags`](https://github.com/Cubelake/appstore-dags)) persists the output to Azure Data Lake Storage.

---

## What it does

- Builds one request URL per **country × feed type** using [`appstore-core`](https://github.com/Cubelake/appstore-core)'s `AppleUrlBuilder`, e.g.:
  ```
  https://rss.marketingtools.apple.com/api/v2/us/apps/top-free/100/apps.json
  ```
- Countries come from a bundled ISO-3166-1 alpha-2 list (~175 codes); feed types are `TOP_FREE` and `TOP_PAID` — so a full run fetches **~350 URLs**.
- Each URL is tagged with a `preset_key` (e.g. `us_top_free`) used downstream to reconstruct `country`/`feed_type` when writing to bronze storage.
- Fetching, batching, retries, and normalization are inherited from `appstore-core`'s `BaseIngestor` — this package only implements `normalize()` and the URL matrix.

## Usage

There's no CLI — it's a library meant to be driven by an orchestrator:

```python
import asyncio
from ingestion_apple_rss.ingestor import Ingestor

records = asyncio.run(Ingestor().collect())
# [{"preset_key": "us_top_free", "url": "...", "feed": {...}}, ...]
```

In production this is called from the `collect_data` task of the `bronze_top_daily` DAG, which writes each record as newline-delimited JSON to `bronze/appstore_rss/snapshot_date=YYYY-MM-DD/` in ADLS.

## Key modules

| File | Responsibility |
|---|---|
| `ingestion_apple_rss/ingestor.py` | `Ingestor(BaseIngestor)` — `get_urls()`, `normalize()`, `collect()` |
| `ingestion_apple_rss/url_factory.py` | `UrlFactory` — cross-joins supported countries × feed types into `(preset_key, url)` pairs |

## Configuration

No environment variables are read by this package. Batching/timeout/retry behavior comes from `appstore-core`'s `IngestionConfig` (`batch_size=10`, `batch_delay_seconds=4.0`, `timeout_seconds=15.0`, `max_retries=2`) and is not currently overridable from here. At `batch_size=10` and `batch_delay_seconds=4.0`, a full ~350-URL run takes roughly 2–3 minutes of enforced pacing alone.

## Install & test

Part of the `cubelake` uv workspace — not published standalone.

```bash
# from the workspace root
uv sync --all-packages
uv run pytest ingestion-apple-rss/tests/ -v
```

`tests/test_url_creation.py` covers URL and preset-key construction (2 parametrized cases against `AppleUrlBuilder`, 2 against `UrlFactory`). Fetch/retry/normalize behavior is exercised indirectly via `appstore-core` and has no dedicated tests here yet.

## Known limitations

- No tests for `Ingestor.collect()` itself (HTTP fetch, retries, normalization) — only URL construction is covered.
- Country list falls back to full `pycountry` enumeration if the bundled resource file is missing, which could silently change the URL count.

## License

[MIT](LICENSE)
