from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


# Bronze
class BronzeMetadata(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source: str = Field(alias="_source")
    ingested_at: str = Field(alias="_ingested_at")
    country: str = Field(alias="_country")
    feed_type: str = Field(alias="_feed_type")

    @classmethod
    def create(cls, source: str, preset_key: str) -> "BronzeMetadata":
        country, feed_type = cls._parse_preset_key(preset_key)
        return cls(
            _source=source,
            _ingested_at=datetime.now(UTC).isoformat(),
            _country=country,
            _feed_type=feed_type,
        )

    @staticmethod
    def _parse_preset_key(preset_key: str) -> tuple[str, str]:
        parts = preset_key.split("_")
        country = (parts[0] if parts else "").lower()
        feed_type = "_".join(parts[1:]).lower()
        return country, feed_type


# Silver


# Gold
