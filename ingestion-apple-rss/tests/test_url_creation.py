import pytest

from apple_rss.model.url_builder import AppleUrlBuilder
from apple_rss.model.url_params import AppleUrlParams, FeedType
from ingestion_apple_rss.url_factory import UrlFactory


RSS_BASE = "https://rss.marketingtools.apple.com/api/v2"


@pytest.mark.parametrize("country,feed_type,expected_url", [
    ("no", FeedType.TOP_FREE, f"{RSS_BASE}/no/apps/top-free/100/apps.json"),
    ("us", FeedType.TOP_PAID, f"{RSS_BASE}/us/apps/top-paid/100/apps.json"),
])
def test_url_builder(country, feed_type, expected_url):
    params = AppleUrlParams(country=country, feed_type=feed_type)
    assert AppleUrlBuilder.build_url(params) == expected_url


@pytest.mark.parametrize("country,feed,expected_key,expected_url", [
    ("no", FeedType.TOP_FREE, "no_top_free", f"{RSS_BASE}/no/apps/top-free/100/apps.json"),
    ("us", FeedType.TOP_PAID, "us_top_paid", f"{RSS_BASE}/us/apps/top-paid/100/apps.json"),
])
def test_url_factory(country, feed, expected_key, expected_url):
    assert UrlFactory.preset_key(country, feed) == expected_key
    assert UrlFactory.get_url_for(country, feed) == expected_url
