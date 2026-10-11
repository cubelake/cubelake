from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """apple-rss configuration (env vars APPLE_RSS_*)."""

    model_config = SettingsConfigDict(env_prefix="APPLE_RSS_")

    bronze_uri: str  # raw chart JSON, e.g. gs://cubelake-bronze/appstore_rss
    silver_uri: str  # silver_top_apps parquet, e.g. gs://cubelake-silver/appstore_rss


def partition(root: str, snapshot_date: str) -> str:
    return f"{root.rstrip('/')}/snapshot_date={snapshot_date}"
