"""Bronze record format shared by all ingestion services.

Keys look like `<country>_<feed_type>` (e.g. `no_top_free`). One JSON-lines file per key:
`<dataset>/snapshot_date=YYYY-MM-DD/<country>_<feed_type>.json`. Keep this format stable —
the BigLake table schemas, silver Dataform models and already-ingested bronze data depend on it.
"""

import json
from datetime import UTC, datetime


def split_key(preset_key: str) -> tuple[str, str]:
    country, _, feed_type = preset_key.lower().partition("_")
    return country, feed_type


def file_name(preset_key: str) -> str:
    country, feed_type = split_key(preset_key)
    return f"{country}_{feed_type}.json"


def record(feed: dict, source: str, preset_key: str) -> str:
    country, feed_type = split_key(preset_key)
    row = {
        "_source": source,
        "_ingested_at": datetime.now(UTC).isoformat(),
        "_feed_type": feed_type,
        "country": country,
        **feed,  # the RSS feed carries its own 'country' with the same value
    }
    return json.dumps(row, ensure_ascii=False) + "\n"
