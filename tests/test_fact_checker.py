"""
Tests for app.services.fact_checker.

Fact checker tests mock the network call (requests.get) rather than hitting
the real Wikipedia API. This keeps tests fast, deterministic, and runnable
without internet access (important for CI/CD pipelines). We cover three
paths: the happy path (valid extract returned), the missing-data path (200
response but no 'extract' field), and the error path (network failure).
"""

from unittest.mock import MagicMock, patch

import requests

from app.services.fact_checker import FALLBACK_MESSAGE, fact_check


@patch("app.services.fact_checker.requests.get")
def test_fact_check_happy_path(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {"extract": "Blockchain is a distributed ledger technology."}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = fact_check("blockchain")

    assert result == "Blockchain is a distributed ledger technology."


@patch("app.services.fact_checker.requests.get")
def test_fact_check_missing_extract_returns_fallback(mock_get):
    mock_response = MagicMock()
    mock_response.json.return_value = {}  # no "extract" key
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    result = fact_check("an obscure made-up topic")

    assert 'I couldn\'t verify "an obscure made-up topic"' in result


@patch("app.services.fact_checker.requests.get")
def test_fact_check_network_error_returns_fallback(mock_get):
    mock_get.side_effect = requests.exceptions.ConnectionError("network down")

    result = fact_check("blockchain")

    assert 'I couldn\'t verify "blockchain"' in result


def test_fact_check_empty_query_returns_fallback():
    assert fact_check("") == FALLBACK_MESSAGE
    assert fact_check("   ") == FALLBACK_MESSAGE


@patch("app.services.fact_checker.requests.get")
def test_fact_check_search_fallback_returns_useful_summary_for_normal_topic(mock_get):
    def fake_get(url, params=None, timeout=None):
        response = MagicMock()
        response.raise_for_status.return_value = None

        if "page/summary/developer_productivity_metrics" in url:
            response.json.return_value = {"type": "https://mediawiki.org/wiki/HyperSwitch/errors/not_found"}
            response.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
            return response

        if "w/api.php" in url:
            response.json.return_value = {
                "query": {
                    "search": [
                        {
                            "title": "Software metric",
                            "snippet": "Software metrics are standard measures used to track productivity and quality.",
                        }
                    ]
                }
            }
            return response

        if "page/summary/Software_metric" in url:
            response.json.return_value = {
                "extract": (
                    "Software metrics are measures of the characteristics of software and the process of software "
                    "development. Teams use them to track productivity, quality, maintainability, and delivery outcomes."
                )
            }
            return response

        raise AssertionError(f"Unexpected URL: {url}")

    mock_get.side_effect = fake_get

    result = fact_check("developer productivity metrics")

    assert "productivity" in result.lower()
    assert "software" in result.lower()
    assert "http" not in result.lower()


@patch("app.services.fact_checker.requests.get")
def test_fact_check_unknown_topic_returns_clear_insufficient_info_message(mock_get):
    def fake_get(url, params=None, timeout=None):
        response = MagicMock()
        response.raise_for_status.return_value = None

        if "page/summary/" in url:
            response.json.return_value = {"type": "https://mediawiki.org/wiki/HyperSwitch/errors/not_found"}
            response.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
            return response

        if "w/api.php" in url:
            response.json.return_value = {"query": {"search": []}}
            return response

        raise AssertionError(f"Unexpected URL: {url}")

    mock_get.side_effect = fake_get

    result = fact_check("zzqvxm unfindable topic")

    assert 'I couldn\'t verify "zzqvxm unfindable topic"' in result
    assert "more specific" in result
