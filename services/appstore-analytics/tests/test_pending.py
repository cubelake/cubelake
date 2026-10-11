from appstore_analytics import pipeline
from appstore_analytics.config import Settings, partition
from appstore_analytics.storage import ensure_dir


def test_pending_silver_needs_both_sources(tmp_path, monkeypatch):
    for name in ("rss_silver", "itunes_silver", "silver", "gold"):
        monkeypatch.setenv(f"APPSTORE_ANALYTICS_{name.upper()}_URI", str(tmp_path / name))
    s = Settings()
    for d in ("2026-10-01", "2026-10-02", "2026-10-03"):
        ensure_dir(partition(s.rss_silver_uri, d))
    for d in ("2026-10-01", "2026-10-02"):
        ensure_dir(partition(s.itunes_silver_uri, d))
    ensure_dir(partition(s.silver_uri, "2026-10-01"))

    assert pipeline.pending_silver(s) == ["2026-10-02"]
    assert pipeline.pending_gold(s) == ["2026-10-01"]
