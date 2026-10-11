import json

from cubelake_extract.apple_rss import pipeline
from cubelake_extract.apple_rss.config import Settings


def test_extract_writes_feed_payload(tmp_path, monkeypatch):
    async def fake_fetch(urls):
        return {u: {"feed": {"country": "no", "results": [{"id": "1"}]}} for u in urls[:2]}

    monkeypatch.setattr(pipeline, "fetch_json", fake_fetch)
    written = pipeline.extract(Settings(bronze_uri=str(tmp_path / "top_charts")), "2026-10-11")

    assert written == 2
    files = sorted((tmp_path / "top_charts/snapshot_date=2026-10-11").iterdir())
    assert len(files) == 2
    assert json.loads(files[0].read_text())["results"] == [{"id": "1"}]
