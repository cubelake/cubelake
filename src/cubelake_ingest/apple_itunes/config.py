from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """apple-itunes ingest configuration (env vars APPLE_ITUNES_*)."""

    model_config = SettingsConfigDict(env_prefix="APPLE_ITUNES_")

    bronze_uri: str       # e.g. gs://cbl-p-bronze-x7k2/apple_itunes/lookup
    top_apps_table: str   # input, e.g. prj-p-cubelake-a1b2.silver_apple_rss.top_apps
