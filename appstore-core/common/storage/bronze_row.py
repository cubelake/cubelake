from pydantic import BaseModel

from common.storage.bronze_metadata import BronzeMetadata
from common.storage.bronze_path_coords import BronzePathCoords


class BronzeRow(BaseModel):
    feed: dict
    metadata: BronzeMetadata
    path_coords: BronzePathCoords

    @classmethod
    def from_raw(cls, feed: dict, source: str, preset_key: str) -> "BronzeRow":
        return cls(
            feed=feed,
            metadata=BronzeMetadata.create(source=source, preset_key=preset_key),
            path_coords=BronzePathCoords.from_preset_key(preset_key),
        )

    def to_record(self) -> dict:
        return {
            **self.metadata.model_dump(by_alias=True),
            "country": self.path_coords.country,
            **self.feed,  # RSS feed already has 'country' and will override with same value
        }
