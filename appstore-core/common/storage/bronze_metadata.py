from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class BronzeMetadata(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source: str = Field(alias="_source")
    ingested_at: str = Field(alias="_ingested_at")
    feed_type: str = Field(alias="_feed_type")

    @classmethod
    def create(cls, source: str, preset_key: str) -> "BronzeMetadata":
        feed_type = "_".join(preset_key.split("_")[1:]).lower()
        return cls(
            _source=source,
            _ingested_at=datetime.now(UTC).isoformat(),
            _feed_type=feed_type,
        )
