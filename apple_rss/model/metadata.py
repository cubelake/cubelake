from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field


class BronzeMetadata(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source: str = Field(alias="_source")
    ingested_at: str = Field(alias="_ingested_at")

    @classmethod
    def create(cls, source: str) -> "BronzeMetadata":
        return cls(
            _source=source,
            _ingested_at=datetime.now(UTC).isoformat(),
        )
