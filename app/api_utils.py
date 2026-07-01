from typing import Any

from fastapi import Query

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def pagination_limit(default: int = DEFAULT_LIMIT):
    return Query(default=default, ge=1, le=MAX_LIMIT)


def pagination_offset():
    return Query(default=0, ge=0)


def normalize_sort_order(sort_order: str) -> bool:
    return sort_order.lower() != "asc"


def paginate_query(query: Any, limit: int, offset: int) -> Any:
    return query.offset(offset).limit(limit)
