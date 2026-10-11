import asyncio
from collections.abc import Iterable

from google.cloud import bigquery
from loguru import logger

from cubelake_ingest.apple_itunes.config import Settings
from cubelake_ingest.apple_itunes.lookup import lookup_urls
from cubelake_ingest.core import bronze
from cubelake_ingest.core.http import fetch_json
from cubelake_ingest.core.storage import partition, write_text

SOURCE = "apple-itunes"


def charted_rows(settings: Settings, snapshot_date: str) -> Iterable[tuple[str, str, int]]:
    """(country, feed_type, app_id) charted that day, read from the apple-rss silver table."""
    client = bigquery.Client()
    job = client.query(
        f"SELECT country, feed_type, app_id FROM `{settings.top_apps_table}` "
        "WHERE snapshot_date = @d AND app_id IS NOT NULL ORDER BY country, feed_type, app_rank",
        job_config=bigquery.QueryJobConfig(
            query_parameters=[bigquery.ScalarQueryParameter("d", "DATE", snapshot_date)]
        ),
    )
    return ((r.country, r.feed_type, r.app_id) for r in job.result())


def group_app_ids(rows: Iterable[tuple[str, str, int]]) -> dict[str, list[str]]:
    """Group by bronze key `<country>_top_<free|paid>`, keeping chart order."""
    ids: dict[str, list[str]] = {}
    for country, feed_type, app_id in rows:
        ids.setdefault(f"{country.lower()}_top_{feed_type.lower()}", []).append(str(app_id))
    return ids


def ingest(settings: Settings, snapshot_date: str, rows: Iterable[tuple[str, str, int]] | None = None) -> int:
    app_ids = group_app_ids(rows if rows is not None else charted_rows(settings, snapshot_date))
    if not app_ids:
        raise RuntimeError(f"No charted apps in {settings.top_apps_table} for {snapshot_date}")

    urls = lookup_urls(app_ids)
    responses = asyncio.run(fetch_json(list(urls.values())))
    key_by_url = {url: key for key, url in urls.items()}

    target = partition(settings.bronze_uri, snapshot_date)
    for url, raw in responses.items():
        key = key_by_url[url]
        write_text(f"{target}/{bronze.file_name(key)}", bronze.record(raw, SOURCE, key))

    logger.info("Wrote {}/{} lookups to {}", len(responses), len(urls), target)
    return len(responses)
