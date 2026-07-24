# appstore-core

> Shared library for the [Cubelake](https://github.com/Cubelake/cubelake) data platform — base ingestion engine, Azure/ADLS storage abstractions, and Pydantic data models for Apple RSS and iTunes sources.

![Python](https://img.shields.io/badge/Python-3.13+-3776AB?logo=python&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-2.x-E92063?logo=pydantic&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-Azure_secrets-FFF000?logo=duckdb&logoColor=black)
![License](https://img.shields.io/badge/License-MIT-green)

This package has no runtime of its own — it is a dependency consumed by [`ingestion-apple-rss`](https://github.com/Cubelake/ingestion-apple-rss), [`ingestion-apple-itunes`](https://github.com/Cubelake/ingestion-apple-itunes), and [`appstore-dags`](https://github.com/Cubelake/appstore-dags) inside the [`cubelake`](https://github.com/Cubelake/cubelake) uv workspace.

---

## What it provides

| Package | Contents |
|---|---|
| `common/` | `BaseIngestor` (async fetch engine), `IngestionConfig`, generic Azure/ADLS storage primitives (bronze row/metadata/path models, container constants, DuckDB secret helpers) |
| `apple_rss/` | RSS feed URL builder, supported-country list, thin re-exports of `common.storage` scoped to the RSS bronze dataset |
| `apple_itunes/` | iTunes Lookup API URL builder/params, thin re-exports of `common.storage` scoped to the iTunes bronze dataset |

## `BaseIngestor`

`common/base_ingestor.py` is the shared engine both ingestion services build on:

```python
class MyIngestor(BaseIngestor):
    def normalize(self, raw: dict) -> list[dict]:
        # turn one raw HTTP JSON response into a list of records
        ...
```

- `normalize(raw: dict) -> list[dict]` is the **only abstract method** — every subclass must implement it.
- `_run_collect(urls: list[str]) -> list[dict]` does the actual work: fetches URLs concurrently in batches via `httpx.AsyncClient`, retries failures, and calls `normalize()` on each successful response. Subclasses populate `self._url_key_map` (url → a "preset key" like `us_top_free`) before calling it, then expose their own public `collect()` method around it — `BaseIngestor` itself does not define `collect()`.
- Batching/retry behavior comes from `IngestionConfig` (`common/ingestion_config.py`), a frozen dataclass with fixed defaults: `batch_size=10`, `batch_delay_seconds=4.0`, `timeout_seconds=15.0`, `max_retries=2`, `retry_delay_seconds=5.0`. These are not currently overridable without subclassing.

## Azure token / storage abstraction

`common/storage/azure_tokens.py` defines `AzureToken` (and per-layer subclasses `BronzeToken`, `SilverToken`, `RssBronzeToken`, `RssSilverToken`, `ItunesBronzeToken`, `ItunesSilverToken`, `AppstoreSilverToken`, `GoldToken`) — each a Pydantic model that loads `account_url` / `sas_token` from environment variables if not passed explicitly:

| Class | Env vars |
|---|---|
| `BronzeToken` | `ACCOUNT_URL`, `BRONZE_SAS_TOKEN` |
| `SilverToken` | `ACCOUNT_URL`, `SILVER_SAS_TOKEN` |
| `RssBronzeToken` | `ACCOUNT_URL`, `BRONZE_RSS_SAS_TOKEN` |
| `RssSilverToken` | `ACCOUNT_URL`, `SILVER_RSS_SAS_TOKEN` |
| `ItunesBronzeToken` | `ACCOUNT_URL`, `BRONZE_ITUNES_SAS_TOKEN` |
| `ItunesSilverToken` | `ACCOUNT_URL`, `SILVER_ITUNES_SAS_TOKEN` |
| `AppstoreSilverToken` | `ACCOUNT_URL`, `SILVER_APPSTORE_SAS_TOKEN` |
| `GoldToken` | `ACCOUNT_URL`, `GOLD_SAS_TOKEN` |

`AzureToken.init_connection(con)` wires a DuckDB connection to ADLS by installing/loading the `httpfs` and `azure` extensions and setting `azure_storage_connection_string` — the same mechanism the Airflow DAGs in `appstore-dags` use to query ADLS directly for snapshot discovery.

## Data models

- `apple_rss.model.url_params.AppleUrlParams` — `country`, `media_type`, `feed_type` (`TOP_FREE`/`TOP_PAID`), `limit`, `schema_type`, `response_format`; built into a request URL by `apple_rss.model.url_builder.AppleUrlBuilder.build_url()`.
- `apple_itunes.model.url_params.AppleItunesUrlParams` — `id: list[str]`, `country: str`; built into a lookup URL by `apple_itunes.model.url_builder.AppleItunesUrlBuilder.build_url()`.
- `common.storage.bronze_row.BronzeRow` — wraps a raw feed record with `BronzeMetadata` (source, ingestion timestamp, feed type) and `BronzePathCoords` (country, feed type derived from the preset key), and flattens into a single dict via `.to_record()`.
- `common.storage.bronze_storage_path.BaseBronzeStoragePath` — builds the Hive-style bronze path `{dataset}/snapshot_date={date}/{country}_{feed_type}.json`; subclassed per source (`apple_rss.storage.bronze_path.AdlsBronzeStoragePath` → dataset `appstore_rss`, `apple_itunes.storage.bronze_path.AdlsBronzeStoragePath` → dataset `appstore_itunes`).

## Install

This package is a member of the `cubelake` uv workspace and is not published standalone. From the workspace root:

```bash
uv sync --all-packages
```

## Known limitations

- No automated tests yet (`tests/` does not exist).
- `duckdb` is imported by `common/storage/azure_tokens.py` but is not declared as a direct dependency in `pyproject.toml` — it's currently pulled in transitively by consumers.
- `apple_apps/` is unused scaffolding, excluded from the built package.

## License

[MIT](LICENSE)
