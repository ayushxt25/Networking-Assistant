from dataclasses import dataclass
from typing import Any

from jose import JWTError, jwt

from app.config import get_supabase_audience, get_supabase_jwt_secret
from app.roles import coerce_user_role


@dataclass
class SupabaseJWTClaims:
    supabase_user_id: str
    email: str | None
    role: str
    raw_claims: dict[str, Any]


def _extract_nested_role(payload: dict[str, Any], key: str) -> str | None:
    nested = payload.get(key)
    if isinstance(nested, dict):
        value = nested.get("role")
        if isinstance(value, str):
            return value
    return None


def _extract_role(payload: dict[str, Any]) -> str:
    candidates = (
        payload.get("role"),
        _extract_nested_role(payload, "app_metadata"),
        _extract_nested_role(payload, "user_metadata"),
        payload.get("app_role"),
        payload.get("user_role"),
    )
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return coerce_user_role(candidate)
    return coerce_user_role(None)


def verify_supabase_jwt(token: str) -> SupabaseJWTClaims | None:
    secret = get_supabase_jwt_secret()
    if not secret:
        return None

    audience = get_supabase_audience()
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience=audience,
        )
    except JWTError:
        return None

    supabase_user_id = payload.get("sub")
    if not isinstance(supabase_user_id, str) or not supabase_user_id.strip():
        return None

    email = payload.get("email")
    return SupabaseJWTClaims(
        supabase_user_id=supabase_user_id,
        email=email if isinstance(email, str) and email.strip() else None,
        role=_extract_role(payload),
        raw_claims=payload,
    )
