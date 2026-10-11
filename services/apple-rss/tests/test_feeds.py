import pytest

from apple_rss.feeds import FeedType, all_feeds, countries, feed_url, preset_key

RSS_BASE = "https://rss.marketingtools.apple.com/api/v2"


@pytest.mark.parametrize("country,feed,expected_key,expected_url", [
    ("no", FeedType.TOP_FREE, "no_top_free", f"{RSS_BASE}/no/apps/top-free/100/apps.json"),
    ("us", FeedType.TOP_PAID, "us_top_paid", f"{RSS_BASE}/us/apps/top-paid/100/apps.json"),
])
def test_feed_url_and_key(country, feed, expected_key, expected_url):
    assert preset_key(country, feed) == expected_key
    assert feed_url(country, feed) == expected_url


def test_all_feeds_covers_every_country_and_feed():
    feeds = all_feeds()
    assert len(countries()) == 175
    assert len(feeds) == 175 * 2
    assert feeds["no_top_free"] == f"{RSS_BASE}/no/apps/top-free/100/apps.json"
