"""
Fact Checker Service
---------------------
Uses Wikipedia as a lightweight external source for quick topic verification.

The service prefers a direct summary lookup first, then falls back to
Wikipedia search when a topic does not map cleanly to a single page. Search
results are only returned when they provide enough signal to be useful. When
they do not, the service returns a clear insufficient-information message
instead of pretending a weak match is reliable.
"""

from __future__ import annotations

import logging
import re
from html import unescape
from urllib.parse import quote

import requests

from app.config import (
    get_fact_check_external_max_results,
    get_fact_check_external_search_enabled,
    get_tavily_api_key,
)
from app.services.external_search import tavily_search

logger = logging.getLogger(__name__)
WIKIPEDIA_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
WIKIPEDIA_SEARCH_URL = "https://en.wikipedia.org/w/api.php"
REQUEST_TIMEOUT_SECONDS = 5
FALLBACK_MESSAGE = (
    "I couldn't verify that topic from the available source right now. "
    "Try a more specific company, product, person, or concept."
)

_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "how",
    "in",
    "is",
    "of",
    "on",
    "or",
    "the",
    "topic",
    "to",
    "what",
    "when",
    "why",
    "with",
}


def _normalize_query(query: str) -> str:
    return " ".join((query or "").strip().split())


def _query_tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", (text or "").lower())
        if len(token) > 2 and token not in _STOPWORDS
    }


def _clean_text(value: str | None) -> str:
    if not value:
        return ""
    text = unescape(value)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _looks_like_disambiguation(data: dict) -> bool:
    page_type = str(data.get("type", "")).lower()
    extract = str(data.get("extract", "")).lower()
    description = str(data.get("description", "")).lower()
    return (
        page_type == "disambiguation"
        or "may refer to" in extract
        or "may stand for" in extract
        or "disambiguation" in description
    )


def _is_useful_summary(summary: str, query: str) -> bool:
    cleaned = _clean_text(summary)
    if not cleaned:
        return False
    if len(cleaned) < 40:
        return False
    if cleaned.count("http://") or cleaned.count("https://"):
        return False
    alpha_words = re.findall(r"[A-Za-z]{3,}", cleaned)
    if len(alpha_words) < 4:
        return False
    tokens = _query_tokens(query)
    if not tokens:
        return False
    overlap = tokens & _query_tokens(cleaned)
    return len(overlap) >= 1


def _fetch_summary(topic: str) -> str:
    url = WIKIPEDIA_SUMMARY_URL.format(quote(topic.replace(" ", "_"), safe="_"))
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    if _looks_like_disambiguation(data):
        return ""
    return _clean_text(data.get("extract"))


def _search_candidates(query: str) -> list[dict]:
    response = requests.get(
        WIKIPEDIA_SEARCH_URL,
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": 5,
            "format": "json",
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("query", {}).get("search", [])


def _candidate_matches_query(query: str, candidate: dict, summary: str) -> bool:
    query_tokens = _query_tokens(query)
    if not query_tokens:
        return False

    candidate_text = " ".join(
        part
        for part in (
            candidate.get("title", ""),
            _clean_text(candidate.get("snippet", "")),
            summary,
        )
        if part
    )
    overlap = query_tokens & _query_tokens(candidate_text)
    return len(overlap) >= 1


def _insufficient_info_message(query: str) -> str:
    if not query:
        return FALLBACK_MESSAGE
    return (
        f'I couldn\'t verify "{query}" from the available source right now. '
        "Try a more specific company, product, person, or concept."
    )


def _is_useful_external_result(result: dict, query: str) -> bool:
    title = _clean_text(result.get("title"))
    content = _clean_text(result.get("content"))
    combined = " ".join(part for part in (title, content) if part)
    if not combined:
        return False
    if len(content) < 40:
        return False
    query_tokens = _query_tokens(query)
    if not query_tokens:
        return False

    overlap = query_tokens & _query_tokens(combined)
    required_overlap = 1 if len(query_tokens) == 1 else 2
    if len(overlap) < required_overlap:
        return False

    return _is_useful_summary(combined, query)


def _build_external_summary(results: list[dict], query: str) -> str:
    useful_bits: list[str] = []
    seen = set()
    rejected_count = 0

    for result in results:
        if not _is_useful_external_result(result, query):
            rejected_count += 1
            continue

        title = _clean_text(result.get("title"))
        content = _clean_text(result.get("content"))
        snippet = content
        if title and title.lower() not in content.lower():
            snippet = f"{title}: {content}"

        key = snippet.lower()
        if key in seen:
            continue
        seen.add(key)
        useful_bits.append(snippet)

        if len(useful_bits) >= 2:
            break

    if not useful_bits:
        if rejected_count:
            logger.info("Tavily weak results rejected feature=fact_check rejected=%s", rejected_count)
        return ""

    summary = " ".join(useful_bits)
    if not _is_useful_summary(summary, query):
        logger.info("Tavily weak results rejected feature=fact_check rejected=%s", max(rejected_count, 1))
        return ""
    return summary


def _fact_check_with_tavily(query: str) -> str:
    if not get_fact_check_external_search_enabled():
        logger.info("Tavily disabled feature=fact_check")
        return ""
    if not get_tavily_api_key():
        logger.info("Tavily missing API key feature=fact_check")
        return ""

    results = tavily_search(
        query,
        max_results=get_fact_check_external_max_results(),
        feature="fact_check",
    )
    return _build_external_summary(results, query)


def fact_check(query: str) -> str:
    """
    Look up a short summary for `query` using Wikipedia.

    The service first tries a direct page-summary request. If that fails or the
    result is too weak, it searches Wikipedia and retries with the best matching
    page titles. Only source-backed text with enough signal is returned.
    """
    normalized_query = _normalize_query(query)
    if not normalized_query:
        return FALLBACK_MESSAGE

    try:
        tavily_summary = _fact_check_with_tavily(normalized_query)
        if tavily_summary:
            return tavily_summary
    except (requests.RequestException, ValueError, KeyError, TypeError):
        logger.info("Fact check fallback used feature=fact_check reason=tavily_unavailable")
        pass

    try:
        direct_summary = _fetch_summary(normalized_query)
        if _is_useful_summary(direct_summary, normalized_query):
            return direct_summary
    except (requests.RequestException, ValueError):
        direct_summary = ""

    try:
        for candidate in _search_candidates(normalized_query):
            title = _clean_text(candidate.get("title"))
            if not title:
                continue
            try:
                candidate_summary = _fetch_summary(title)
            except (requests.RequestException, ValueError):
                continue

            if _is_useful_summary(candidate_summary, normalized_query) and _candidate_matches_query(
                normalized_query, candidate, candidate_summary
            ):
                return candidate_summary
    except (requests.RequestException, ValueError):
        pass

    logger.info("Fact check fallback used feature=fact_check reason=insufficient_info")
    return _insufficient_info_message(normalized_query)
