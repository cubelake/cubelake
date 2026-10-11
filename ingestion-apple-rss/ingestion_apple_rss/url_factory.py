from apple_rss.model.supported_countries import SupportedCountries
from apple_rss.model.url_builder import AppleUrlBuilder
from apple_rss.model.url_params import AppleUrlParams, FeedType


class UrlFactory:
    SUPPORTED_COUNTRIES: tuple[str, ...] = SupportedCountries.load_countries()
    SUPPORTED_FEEDS: tuple[FeedType, ...] = (FeedType.TOP_FREE, FeedType.TOP_PAID)

    @classmethod
    def preset_key(cls, country: str, feed: FeedType) -> str:
        return f"{country.lower()}_{feed.name.lower()}"

    @classmethod
    def get_url_for(cls, country: str, feed: FeedType) -> str:
        params = AppleUrlParams(country=country, feed_type=feed, limit=100)
        return AppleUrlBuilder.build_url(params)

    @classmethod
    def list_all_urls_with_keys(cls) -> list[tuple[str, str]]:
        return [
            (cls.preset_key(country, feed), cls.get_url_for(country, feed))
            for country in cls.SUPPORTED_COUNTRIES
            for feed in cls.SUPPORTED_FEEDS
        ]
