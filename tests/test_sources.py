from unittest.mock import Mock, patch

import pytest
import requests

from data_extraction.sources import FixtureSource, HttpSource


def test_fixture_aliases_and_gone(fixture_dir):
    source = FixtureSource(fixture_dir)
    rows = list(source.records(26))
    assert len({url for url, date in rows}) == 26
    assert source.fetch(rows[0][0]) == source.fetch(rows[13][0])
    assert source.fetch(rows[12][0]) == (410, None)
    with pytest.raises(ValueError):
        source.fetch("https://example.invalid/")


def test_http_backoff_is_only_mocked():
    responses = [
        Mock(status_code=429),
        Mock(status_code=503),
        Mock(status_code=200, text="HTML"),
    ]
    for response in responses:
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
    with (
        patch("data_extraction.sources.requests.get", side_effect=responses) as get,
        patch("data_extraction.sources.time.sleep") as sleep,
    ):
        assert HttpSource().fetch("https://example.invalid/") == (200, "HTML")
    assert [call.args[0] for call in sleep.call_args_list] == [1, 2]
    assert get.call_count == 3
    assert get.call_args.kwargs["headers"]["User-Agent"]
    assert get.call_args.kwargs["timeout"] > 0
    assert get.call_args.kwargs["allow_redirects"] is False


def test_http_timeout_exhaustion_is_only_mocked():
    with (
        patch("data_extraction.sources.requests.get", side_effect=requests.Timeout),
        patch("data_extraction.sources.time.sleep"),
    ):
        assert HttpSource().fetch("https://example.invalid/") == (None, None)
