from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """apple-itunes configuration (env vars APPLE_ITUNES_*)."""

    model_config = SettingsConfigDict(env_prefix="APPLE_ITUNES_")

    rss_silver_uri: str  # input: apple-rss silver_top_apps, e.g. gs://cubelake-silver/appstore_rss
    bronze_uri: str  # raw lookup JSON, e.g. gs://cubelake-bronze/appstore_itunes
    silver_uri: str  # silver_itunes_app_details parquet, e.g. gs://cubelake-silver/appstore_itunes


def partition(root: str, snapshot_date: str) -> str:
    return f"{root.rstrip('/')}/snapshot_date={snapshot_date}"
