from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """appstore-analytics configuration (env vars APPSTORE_ANALYTICS_*)."""

    model_config = SettingsConfigDict(env_prefix="APPSTORE_ANALYTICS_")

    rss_silver_uri: str  # input: apple-rss silver, e.g. gs://cubelake-silver/appstore_rss
    itunes_silver_uri: str  # input: apple-itunes silver, e.g. gs://cubelake-silver/appstore_itunes
    silver_uri: str  # joined silver_appstore_apps, e.g. gs://cubelake-silver/appstore
    gold_uri: str  # gold marts root, e.g. gs://cubelake-gold


def partition(root: str, snapshot_date: str) -> str:
    return f"{root.rstrip('/')}/snapshot_date={snapshot_date}"
