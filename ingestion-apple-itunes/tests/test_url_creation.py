import pytest

from apple_itunes.model.url_builder import AppleItunesUrlBuilder
from apple_itunes.model.url_params import AppleItunesUrlParams
from ingestion_apple_itunes.url_factory import UrlFactory


ITUNES_BASE = "https://itunes.apple.com/lookup"


@pytest.mark.parametrize("ids,country,expected_url", [
    (["324684580"], "no", f"{ITUNES_BASE}?id=324684580&country=no"),
    (["324684580", "544007664", "310633997"], "no", f"{ITUNES_BASE}?id=324684580,544007664,310633997&country=no"),
])
def test_url_builder(ids, country, expected_url):
    params = AppleItunesUrlParams(id=ids, country=country)
    assert AppleItunesUrlBuilder.build_url(params) == expected_url


@pytest.mark.parametrize("app_ids_by_key,expected_results", [
    (
        {"no_top_free": ["324684580", "544007664"]},
        [("no_top_free", f"{ITUNES_BASE}?id=324684580,544007664&country=no")],
    ),
    (
        {"us_top_paid": ["111"], "no_top_free": []},
        [("us_top_paid", f"{ITUNES_BASE}?id=111&country=us")],
    ),
])
def test_url_factory(app_ids_by_key, expected_results):
    assert UrlFactory.list_all_urls_with_keys(app_ids_by_key) == expected_results
