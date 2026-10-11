import asyncio
from pathlib import Path

from loguru import logger

from apple_itunes import bronze
from apple_itunes.config import Settings, partition
from apple_itunes.dbt import run_dbt
from apple_itunes.http import fetch_json
from apple_itunes.lookup import lookup_urls
from apple_itunes.storage import duckdb_connect, ensure_dir, snapshot_dates, write_text

SOURCE = "apple-itunes"
DBT_DIR = Path(__file__).resolve().parents[2] / "dbt"


def charted_app_ids(settings: Settings, snapshot_date: str) -> dict[str, list[str]]:
    """App ids from apple-rss silver for one day, grouped by `<country>_top_<free|paid>`."""
    source = f"{partition(settings.rss_silver_uri, snapshot_date)}/*.parquet"
    with duckdb_connect(source) as con:
        rows = con.execute(
            "SELECT country, feed_type, app_id FROM read_parquet(?) "
            "WHERE app_id IS NOT NULL ORDER BY app_rank",
            [source],
        ).fetchall()

    ids: dict[str, list[str]] = {}
    for country, feed_type, app_id in rows:
        ids.setdefault(f"{country.lower()}_top_{feed_type.lower()}", []).append(str(app_id))
    return ids


def extract(settings: Settings, snapshot_date: str) -> int:
    urls = lookup_urls(charted_app_ids(settings, snapshot_date))
    responses = asyncio.run(fetch_json(list(urls.values())))
    key_by_url = {url: key for key, url in urls.items()}

    target = partition(settings.bronze_uri, snapshot_date)
    for url, raw in responses.items():
        key = key_by_url[url]
        write_text(f"{target}/{bronze.file_name(key)}", bronze.record(raw, SOURCE, key))

    logger.info("Wrote {} bronze files to {}", len(responses), target)
    return len(responses)


def pending_extract(settings: Settings) -> list[str]:
    """apple-rss silver days we haven't looked up yet."""
    return sorted(snapshot_dates(settings.rss_silver_uri) - snapshot_dates(settings.bronze_uri))


def pending_transform(settings: Settings) -> list[str]:
    return sorted(snapshot_dates(settings.bronze_uri) - snapshot_dates(settings.silver_uri))


def transform(settings: Settings, snapshot_date: str) -> None:
    ensure_dir(partition(settings.silver_uri, snapshot_date))
    run_dbt(DBT_DIR, "+silver_itunes_app_details", {"snapshot_date": snapshot_date})
