"""
Auth Dependency
-----------------
Provides get_current_user, a FastAPI dependency that extracts the bearer
token from the Authorization header, validates it, and loads the
corresponding User from the database. Any route that depends on this is
automatically protected -- requests without a valid token receive a 401
before the route handler body ever runs.

Note on OAuth2PasswordBearer: it's used here purely as a convenient way to
extract and validate "Authorization: Bearer <token>" headers, NOT to
enforce the full OAuth2 password-grant flow. Our actual /auth/login
endpoint accepts a plain JSON body (UserLoginRequest), not OAuth2's
required form-encoded username/password fields. One consequence: the
"Authorize" button in the auto-generated Swagger UI at /docs expects
form-encoded credentials and will not work against our JSON login endpoint.
To try protected endpoints interactively, log in via POST /auth/login
(e.g. with curl or the Streamlit frontend) and paste the resulting token
into Swagger's Authorize dialog directly instead.
"""

import re

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth import create_unusable_password_hash, decode_access_token
from app.config import get_supabase_auth_enabled, get_supabase_dual_auth_enabled
from app.database import get_db
from app.db_models import User
from app.roles import coerce_user_role
from app.supabase_auth import SupabaseJWTClaims, verify_supabase_jwt

# tokenUrl points at the login endpoint; this only affects the auto-generated
# Swagger UI's "Authorize" button, not runtime behavior.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def _build_credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _get_legacy_user(token: str, db: Session) -> User | None:
    username = decode_access_token(token)
    if username is None:
        return None
    return db.query(User).filter(User.username == username).first()


def _derive_supabase_username(email: str | None, supabase_user_id: str) -> str:
    base_value = (email or "").split("@", 1)[0].strip().lower()
    base_value = re.sub(r"[^a-z0-9_.-]+", "_", base_value).strip("._-")
    if len(base_value) < 3:
        base_value = f"sb_{supabase_user_id.replace('-', '_')[:16]}".strip("._-")
    return (base_value or f"sb_{supabase_user_id[:12]}")[:64]


def _next_available_username(db: Session, base_username: str) -> str:
    candidate = base_username[:64]
    suffix = 1
    while db.query(User).filter(User.username == candidate).first() is not None:
        suffix_token = f"_{suffix}"
        candidate = f"{base_username[: max(1, 64 - len(suffix_token))]}{suffix_token}"
        suffix += 1
    return candidate


def _get_or_create_supabase_user(claims: SupabaseJWTClaims, db: Session) -> User:
    user = db.query(User).filter(User.supabase_user_id == claims.supabase_user_id).first()
    if user is not None:
        if not getattr(user, "role", None):
            user.role = coerce_user_role(claims.role)
            db.commit()
            db.refresh(user)
        return user

    username = _next_available_username(
        db,
        _derive_supabase_username(claims.email, claims.supabase_user_id),
    )
    user = User(
        username=username,
        supabase_user_id=claims.supabase_user_id,
        role=coerce_user_role(claims.role),
        hashed_password=create_unusable_password_hash(claims.supabase_user_id),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _get_supabase_user(token: str, db: Session) -> User | None:
    claims = verify_supabase_jwt(token)
    if claims is None:
        return None
    return _get_or_create_supabase_user(claims, db)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = _build_credentials_exception()

    if not get_supabase_auth_enabled():
        user = _get_legacy_user(token, db)
        if user is None:
            raise credentials_exception
        return user

    if get_supabase_dual_auth_enabled():
        legacy_user = _get_legacy_user(token, db)
        if legacy_user is not None:
            return legacy_user

    supabase_user = _get_supabase_user(token, db)
    if supabase_user is not None:
        return supabase_user

    if not get_supabase_dual_auth_enabled():
        raise credentials_exception

    raise credentials_exception
