from pydantic import BaseModel

# https://itunes.apple.com/lookup?id=324684580,544007664,310633997&country=no


class AppleItunesUrlParams(BaseModel):
    id: list[str]
    country: str
