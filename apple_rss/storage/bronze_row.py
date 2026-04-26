from pydantic import BaseModel

from apple_rss.storage.metadata import BronzeMetadata
from apple_rss.storage.path_coords import BronzePathCoords


class BronzeRow(BaseModel):
    feed: dict
    metadata: BronzeMetadata
    path_coords: BronzePathCoords

    @classmethod
    def from_raw(cls, feed: dict, source: str, preset_key: str) -> "BronzeRow":
        return cls(
            feed=feed,
            metadata=BronzeMetadata.create(source=source,preset_key=preset_key),
            path_coords=BronzePathCoords.from_preset_key(preset_key),
        )

    def to_record(self) -> dict:
        return {**self.metadata.model_dump(by_alias=True), **self.feed}
