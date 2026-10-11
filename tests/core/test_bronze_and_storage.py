import json

from cubelake_ingest.core import bronze
from cubelake_ingest.core.storage import partition, write_text


def test_bronze_record_keeps_stable_format():
    row = json.loads(bronze.record({"title": "x"}, "apple-rss", "no_top_free"))
    assert row["_source"] == "apple-rss"
    assert row["_feed_type"] == "top_free"
    assert row["country"] == "no"
    assert row["title"] == "x"
    assert "snapshot_date" not in row  # hive partition key must not appear inside the files
    assert bronze.file_name("NO_top_free") == "no_top_free.json"


def test_write_hive_partition(tmp_path):
    target = partition(str(tmp_path / "apple_rss" / "top_charts") + "/", "2026-10-11")
    write_text(f"{target}/no_top_free.json", '{"a": 1}\n')
    assert (tmp_path / "apple_rss/top_charts/snapshot_date=2026-10-11/no_top_free.json").read_text() == '{"a": 1}\n'
