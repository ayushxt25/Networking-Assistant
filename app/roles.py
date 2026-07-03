ALLOWED_USER_ROLES = {"user", "admin"}
DEFAULT_ROLE = "user"
ADMIN_ROLE = "admin"


def normalize_user_role(role: str | None) -> str:
    normalized = (role or DEFAULT_ROLE).strip().lower()
    if normalized not in ALLOWED_USER_ROLES:
        raise ValueError(f"role must be one of {sorted(ALLOWED_USER_ROLES)}")
    return normalized


def coerce_user_role(role: str | None) -> str:
    try:
        return normalize_user_role(role)
    except ValueError:
        return DEFAULT_ROLE


def is_admin_role(role: str | None) -> bool:
    return normalize_user_role(role) == ADMIN_ROLE
