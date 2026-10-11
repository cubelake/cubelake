import json
from enum import StrEnum
from importlib.resources import files

BASE_URL = "https://rss.marketingtools.apple.com/api/v2"


class FeedType(StrEnum):
    TOP_FREE = "top-free"
    TOP_PAID = "top-paid"


def countries() -> tuple[str, ...]:
    return tuple(json.loads(files("cubelake_extract.apple_rss").joinpath("countries.json").read_text("utf-8")))


def preset_key(country: str, feed: FeedType) -> str:
    return f"{country.lower()}_{feed.name.lower()}"


# https://rss.marketingtools.apple.com/api/v2/no/apps/top-free/100/apps.json
def feed_url(country: str, feed: FeedType, limit: int = 100) -> str:
    return f"{BASE_URL}/{country}/apps/{feed.value}/{limit}/apps.json"


def all_feeds() -> dict[str, str]:
    """preset_key -> URL for every supported country and feed."""
    return {
        preset_key(country, feed): feed_url(country, feed)
        for country in countries()
        for feed in FeedType
    }
