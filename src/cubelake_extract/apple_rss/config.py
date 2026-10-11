from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """apple-rss extract configuration (env vars APPLE_RSS_*)."""

    model_config = SettingsConfigDict(env_prefix="APPLE_RSS_")

    bronze_uri: str  # e.g. gs://cbl-p-bronze-x7k2/apple_rss/top_charts
