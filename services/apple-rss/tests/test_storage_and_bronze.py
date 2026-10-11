import json

from apple_rss import bronze
from apple_rss.config import partition
from apple_rss.storage import ensure_dir, snapshot_dates, write_text


def test_bronze_record_keeps_stable_format():
    row = json.loads(bronze.record({"title": "x"}, "apple-rss", "no_top_free"))
    assert row["_source"] == "apple-rss"
    assert row["_feed_type"] == "top_free"
    assert row["country"] == "no"
    assert row["title"] == "x"
    assert bronze.file_name("NO_top_free") == "no_top_free.json"


def test_local_storage_roundtrip(tmp_path):
    root = str(tmp_path / "bronze") + "/"
    assert snapshot_dates(root) == set()
    write_text(f"{partition(root, '2026-10-01')}/no_top_free.json", "{}\n")
    ensure_dir(partition(root, "2026-10-02"))
    assert snapshot_dates(root) == {"2026-10-01", "2026-10-02"}
