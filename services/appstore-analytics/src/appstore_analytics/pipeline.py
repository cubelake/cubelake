from pathlib import Path

from appstore_analytics.config import Settings, partition
from appstore_analytics.dbt import run_dbt
from appstore_analytics.storage import ensure_dir, snapshot_dates

DBT_DIR = Path(__file__).resolve().parents[2] / "dbt"


def gold(settings: Settings, mart: str) -> str:
    return f"{settings.gold_uri.rstrip('/')}/{mart}"


def pending_silver(settings: Settings) -> list[str]:
    """Days where both sources are in silver but the joined table isn't built yet."""
    ready = snapshot_dates(settings.rss_silver_uri) & snapshot_dates(settings.itunes_silver_uri)
    return sorted(ready - snapshot_dates(settings.silver_uri))


def pending_gold(settings: Settings) -> list[str]:
    return sorted(snapshot_dates(settings.silver_uri) - snapshot_dates(gold(settings, "fct_top_apps")))


def build_silver(settings: Settings, snapshot_date: str) -> None:
    ensure_dir(partition(settings.silver_uri, snapshot_date))
    run_dbt(DBT_DIR, "silver_appstore_apps", {"snapshot_date": snapshot_date})


def build_gold_daily(settings: Settings, snapshot_date: str) -> None:
    for mart in ("fct_top_apps", "fct_genre_stats"):
        ensure_dir(partition(gold(settings, mart), snapshot_date))
    run_dbt(DBT_DIR, "gold_fct_top_apps gold_fct_genre_stats", {"snapshot_date": snapshot_date})


def build_dim_apps(settings: Settings) -> None:
    ensure_dir(gold(settings, "dim_apps"))
    run_dbt(DBT_DIR, "gold_dim_apps")


def build_rank_history(settings: Settings) -> None:
    """Full recompute over every silver snapshot."""
    ensure_dir(gold(settings, "fct_app_rank_history"))
    run_dbt(DBT_DIR, "gold_fct_app_rank_history")
