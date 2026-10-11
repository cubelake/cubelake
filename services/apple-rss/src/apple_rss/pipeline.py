import asyncio
from pathlib import Path

from loguru import logger

from apple_rss import bronze
from apple_rss.config import Settings, partition
from apple_rss.dbt import run_dbt
from apple_rss.feeds import all_feeds
from apple_rss.http import fetch_json
from apple_rss.storage import ensure_dir, snapshot_dates, write_text

SOURCE = "apple-rss"
DBT_DIR = Path(__file__).resolve().parents[2] / "dbt"


def extract(settings: Settings, snapshot_date: str) -> int:
    """Fetch every top chart and write one bronze JSON file per country/feed."""
    feeds = all_feeds()
    responses = asyncio.run(fetch_json(list(feeds.values())))
    key_by_url = {url: key for key, url in feeds.items()}

    target = partition(settings.bronze_uri, snapshot_date)
    for url, raw in responses.items():
        key = key_by_url[url]
        write_text(f"{target}/{bronze.file_name(key)}", bronze.record(raw.get("feed") or {}, SOURCE, key))

    logger.info("Wrote {} bronze files to {}", len(responses), target)
    return len(responses)


def pending(settings: Settings) -> list[str]:
    """Bronze snapshots that have no silver output yet."""
    return sorted(snapshot_dates(settings.bronze_uri) - snapshot_dates(settings.silver_uri))


def transform(settings: Settings, snapshot_date: str) -> None:
    ensure_dir(partition(settings.silver_uri, snapshot_date))
    run_dbt(DBT_DIR, "+silver_top_apps", {"snapshot_date": snapshot_date})
