from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class BronzeMetadata(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source: str = Field(alias="_source")
    ingested_at: str = Field(alias="_ingested_at")
    feed_type: str = Field(alias="_feed_type")

    @classmethod
    def create(cls, source: str, preset_key: str) -> "BronzeMetadata":
        feed_type = cls._parse_feed_type(preset_key)
        return cls(
            _source=source,
            _ingested_at=datetime.now(UTC).isoformat(),
            _feed_type=feed_type,
        )

    @staticmethod
    def _parse_feed_type(preset_key: str) -> str:
        parts = preset_key.split("_")
        return "_".join(parts[1:]).lower()
