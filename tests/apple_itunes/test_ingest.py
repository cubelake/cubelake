import json

import pytest

from cubelake_ingest.apple_itunes import ingest
from cubelake_ingest.apple_itunes.config import Settings


def test_group_app_ids_keeps_chart_order():
    rows = [("NO", "free", 3), ("NO", "free", 1), ("US", "paid", 7)]
    assert ingest.group_app_ids(rows) == {"no_top_free": ["3", "1"], "us_top_paid": ["7"]}


def test_ingest_writes_one_file_per_chart(tmp_path, monkeypatch):
    async def fake_fetch(urls):
        return {u: {"resultCount": 1, "results": [{"trackId": 1}]} for u in urls}

    monkeypatch.setattr(ingest, "fetch_json", fake_fetch)
    settings = Settings(bronze_uri=str(tmp_path / "lookup"), top_apps_table="p.silver_apple_rss.top_apps")

    written = ingest.ingest(settings, "2026-10-11", rows=[("NO", "free", 1), ("US", "paid", 2)])

    assert written == 2
    row = json.loads((tmp_path / "lookup/snapshot_date=2026-10-11/no_top_free.json").read_text())
    assert row["_source"] == "apple-itunes" and row["resultCount"] == 1


def test_ingest_fails_without_charted_apps(tmp_path):
    settings = Settings(bronze_uri=str(tmp_path), top_apps_table="p.silver_apple_rss.top_apps")
    with pytest.raises(RuntimeError, match="No charted apps"):
        ingest.ingest(settings, "2026-10-11", rows=[])
