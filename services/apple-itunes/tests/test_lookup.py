import pytest

from apple_itunes.lookup import lookup_url, lookup_urls

ITUNES_BASE = "https://itunes.apple.com/lookup"


@pytest.mark.parametrize("ids,country,expected_url", [
    (["324684580"], "no", f"{ITUNES_BASE}?id=324684580&country=no"),
    (["324684580", "544007664", "310633997"], "no", f"{ITUNES_BASE}?id=324684580,544007664,310633997&country=no"),
])
def test_lookup_url(ids, country, expected_url):
    assert lookup_url(ids, country) == expected_url


@pytest.mark.parametrize("app_ids_by_key,expected", [
    (
        {"no_top_free": ["324684580", "544007664"]},
        {"no_top_free": f"{ITUNES_BASE}?id=324684580,544007664&country=no"},
    ),
    (
        {"us_top_paid": ["111"], "no_top_free": []},
        {"us_top_paid": f"{ITUNES_BASE}?id=111&country=us"},
    ),
])
def test_lookup_urls(app_ids_by_key, expected):
    assert lookup_urls(app_ids_by_key) == expected
