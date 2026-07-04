from __future__ import annotations

import logging
from typing import Any

import requests

from app.config import (
    get_external_search_timeout_seconds,
    get_fact_check_external_max_results,
    get_tavily_api_key,
)

TAVILY_SEARCH_URL = "https://api.tavily.com/search"
logger = logging.getLogger(__name__)


def tavily_search(
    query: str,
    max_results: int | None = None,
    *,
    feature: str = "unknown",
) -> list[dict[str, Any]]:
    api_key = get_tavily_api_key()
    if not api_key:
        logger.info("Tavily skipped: missing API key feature=%s", feature)
        return []

    requested_results = max_results or get_fact_check_external_max_results()
    logger.info("Tavily request attempted feature=%s max_results=%s", feature, requested_results)

    try:
        response = requests.post(
            TAVILY_SEARCH_URL,
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "basic",
                "max_results": requested_results,
                "include_answer": False,
                "include_raw_content": False,
            },
            timeout=get_external_search_timeout_seconds(),
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        logger.info("Tavily success feature=%s result_count=%s", feature, len(results))
        return results
    except requests.Timeout:
        logger.warning("Tavily timeout feature=%s", feature)
        raise
    except requests.RequestException:
        logger.warning("Tavily request error feature=%s", feature)
        raise
