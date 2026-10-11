import asyncio

from loguru import logger

from cubelake_ingest.apple_rss.config import Settings
from cubelake_ingest.apple_rss.feeds import all_feeds
from cubelake_ingest.core import bronze
from cubelake_ingest.core.http import fetch_json
from cubelake_ingest.core.storage import partition, write_text

SOURCE = "apple-rss"


def ingest(settings: Settings, snapshot_date: str) -> int:
    """Fetch every top chart and write one raw NDJSON file per country/feed."""
    feeds = all_feeds()
    responses = asyncio.run(fetch_json(list(feeds.values())))
    key_by_url = {url: key for key, url in feeds.items()}

    target = partition(settings.bronze_uri, snapshot_date)
    for url, raw in responses.items():
        key = key_by_url[url]
        write_text(f"{target}/{bronze.file_name(key)}", bronze.record(raw.get("feed") or {}, SOURCE, key))

    logger.info("Wrote {}/{} feeds to {}", len(responses), len(feeds), target)
    if not responses:
        raise RuntimeError("No feed could be fetched")
    return len(responses)
