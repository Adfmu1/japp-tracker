from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import current_user

# Shared limiter so blueprints can attach per-route limits. Storage and the
# enabled flag come from the app config (RATELIMIT_*).
limiter = Limiter(key_func=get_remote_address)


def login_rate_limit_key() -> str:
    """Key login attempts on client address plus the attempted username.

    This throttles both a single account being hammered from one address and
    password spraying that reuses the same username.
    """
    username = (request.form.get("username") or "").strip().lower()
    return f"{get_remote_address()}:{username or '-'}"


def user_rate_limit_key() -> str:
    """Key authenticated actions on the user id, falling back to the address."""
    if current_user.is_authenticated:
        return f"user:{current_user.id}"
    return get_remote_address()
