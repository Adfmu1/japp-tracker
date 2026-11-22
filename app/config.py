import os
from datetime import timedelta
from typing import ClassVar

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ["SECRET_KEY"]
    SQLALCHEMY_DATABASE_URI = os.environ["DB_URL"]

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Cookies must stay usable over plain HTTP during local development.
    SESSION_COOKIE_SECURE = False
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_SECURE = False
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)

    MAX_CONTENT_LENGTH = 1024 * 1024
    SQLALCHEMY_ENGINE_OPTIONS: ClassVar[dict[str, bool]] = {"pool_pre_ping": True}

    if len(SECRET_KEY) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters long")


class ProductionConfig(Config):
    """Production config: session and remember cookies require HTTPS."""

    SESSION_COOKIE_SECURE = True
    REMEMBER_COOKIE_SECURE = True


def get_config() -> type[Config]:
    if os.environ.get("APP_ENV") == "production":
        return ProductionConfig
    return Config
