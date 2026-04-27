from pydantic import BaseModel


class BronzePathCoords(BaseModel):
    country: str
    feed_type: str

    @classmethod
    def from_preset_key(cls, preset_key: str) -> "BronzePathCoords":
        parts = preset_key.split("_")
        country = (parts[0] if parts else "").lower()
        feed_type = "_".join(parts[1:]).lower()
        return cls(country=country, feed_type=feed_type)
