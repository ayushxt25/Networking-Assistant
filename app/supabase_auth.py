from dataclasses import dataclass
import json
import logging
from time import time
from typing import Any
from urllib.request import urlopen

from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode

from app.config import get_supabase_audience, get_supabase_jwks_url, get_supabase_jwt_secret
from app.roles import coerce_user_role

logger = logging.getLogger("networking_assistant")
_JWKS_CACHE: dict[str, list[dict[str, Any]]] = {}


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


def _decode_with_shared_secret(token: str, secret: str) -> dict[str, Any] | None:
    audience = get_supabase_audience()
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience=audience,
        )
        logger.info("Supabase JWT verified via shared secret")
        return payload
    except JWTError as exc:
        logger.warning("Supabase shared-secret verification failed: %s", exc.__class__.__name__)
        return None


def _fetch_jwks(jwks_url: str) -> list[dict[str, Any]]:
    with urlopen(jwks_url, timeout=3) as response:
        payload = json.loads(response.read().decode("utf-8"))
    keys = payload.get("keys")
    if not isinstance(keys, list):
        raise ValueError("JWKS payload does not contain a keys list")
    return [item for item in keys if isinstance(item, dict)]


def _get_jwks(jwks_url: str, *, refresh: bool = False) -> list[dict[str, Any]]:
    if refresh or jwks_url not in _JWKS_CACHE:
        _JWKS_CACHE[jwks_url] = _fetch_jwks(jwks_url)
    return _JWKS_CACHE[jwks_url]


def _get_matching_jwk(keys: list[dict[str, Any]], kid: str | None, algorithm: str | None) -> dict[str, Any] | None:
    for key_data in keys:
        if kid and key_data.get("kid") == kid:
            return key_data
    for key_data in keys:
        if algorithm and key_data.get("alg") in {None, algorithm}:
            return key_data
    return None


def _validate_registered_claims(claims: dict[str, Any]) -> bool:
    audience = get_supabase_audience()
    aud = claims.get("aud")
    if isinstance(aud, str):
        if aud != audience:
            return False
    elif isinstance(aud, list):
        if audience not in aud:
            return False
    else:
        return False

    now = int(time())
    exp = claims.get("exp")
    if isinstance(exp, (int, float)) and exp < now:
        return False

    nbf = claims.get("nbf")
    if isinstance(nbf, (int, float)) and nbf > now:
        return False

    return True


def _decode_with_jwks(token: str) -> dict[str, Any] | None:
    jwks_url = get_supabase_jwks_url()
    if not jwks_url:
        return None

    try:
        header = jwt.get_unverified_header(token)
        claims = jwt.get_unverified_claims(token)
    except JWTError as exc:
        logger.warning("Supabase JWT header/claim extraction failed: %s", exc.__class__.__name__)
        return None

    algorithm = header.get("alg")
    kid = header.get("kid")
    signing_input, encoded_signature = token.rsplit(".", 1)
    decoded_signature = base64url_decode(encoded_signature.encode("utf-8"))

    for refresh in (False, True):
        try:
            keys = _get_jwks(jwks_url, refresh=refresh)
        except Exception as exc:
            logger.warning("Supabase JWKS fetch failed: %s", exc.__class__.__name__)
            return None

        key_data = _get_matching_jwk(keys, kid, algorithm)
        if key_data is None:
            continue

        try:
            verifier = jwk.construct(key_data, algorithm=algorithm)
            if not verifier.verify(signing_input.encode("utf-8"), decoded_signature):
                continue
        except Exception as exc:
            logger.warning("Supabase JWKS verification failed: %s", exc.__class__.__name__)
            continue

        if not _validate_registered_claims(claims):
            logger.warning("Supabase JWKS claims validation failed")
            return None

        logger.info("Supabase JWT verified via JWKS")
        return claims

    logger.warning("Supabase JWKS verification failed: no matching signing key")
    return None


def verify_supabase_jwt(token: str) -> SupabaseJWTClaims | None:
    try:
        header = jwt.get_unverified_header(token)
    except JWTError as exc:
        logger.warning("Supabase JWT header extraction failed: %s", exc.__class__.__name__)
        return None
    algorithm = header.get("alg")

    payload: dict[str, Any] | None = None
    secret = get_supabase_jwt_secret()
    if algorithm == "HS256" and secret:
        payload = _decode_with_shared_secret(token, secret)
    elif get_supabase_jwks_url():
        payload = _decode_with_jwks(token)

    if payload is None and algorithm != "HS256" and secret:
        payload = _decode_with_shared_secret(token, secret)
    if payload is None and algorithm == "HS256" and get_supabase_jwks_url():
        payload = _decode_with_jwks(token)
    if payload is None:
        return None

    supabase_user_id = payload.get("sub")
    if not isinstance(supabase_user_id, str) or not supabase_user_id.strip():
        logger.warning("Supabase JWT missing valid sub claim")
        return None

    email = payload.get("email")
    return SupabaseJWTClaims(
        supabase_user_id=supabase_user_id,
        email=email if isinstance(email, str) and email.strip() else None,
        role=_extract_role(payload),
        raw_claims=payload,
    )
