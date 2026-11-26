import uuid

from flask import Flask, render_template, request
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf import CSRFProtect

from .config import Config, get_config
from .extensions import limiter
from .models import User, db
from .routes.account import bp as account_bp
from .routes.applications import bp as applications_bp
from .routes.auth import bp as auth_bp
from .routes.main import bp as main_bp

login_manager = LoginManager()
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    try:
        return db.session.get(User, uuid.UUID(user_id))
    except (ValueError, TypeError):
        return None


def create_app(config_object: type[Config] | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_object or get_config())

    db.init_app(app)
    Migrate(app, db)
    csrf.init_app(app)
    limiter.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @app.after_request
    def add_security_headers(response):
        response.headers.update(
            {
                "Content-Security-Policy": (
                    "default-src 'self'; base-uri 'self'; object-src 'none'; "
                    "frame-ancestors 'none'; script-src 'self'; style-src 'self'; "
                    "img-src 'self' data:; font-src 'self'; connect-src 'self'"
                ),
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "strict-origin-when-cross-origin",
                "X-Frame-Options": "DENY",
            }
        )
        if app.config.get("SECURITY_HEADERS_HSTS", False):
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    @app.errorhandler(429)
    def ratelimit_handler(error: Exception) -> tuple[str, int]:
        # Log the endpoint and address only; never the submitted username or
        # any other request body, so breach records cannot leak credentials.
        app.logger.warning(
            "Rate limit exceeded on %s from %s",
            request.endpoint,
            request.remote_addr,
        )
        return render_template("ratelimit.html"), 429

    # A process-local store cannot enforce limits across workers or survive a
    # restart, so flag any memory-backed scheme outside local development.
    if (
        "memory://" in str(app.config["RATELIMIT_STORAGE_URI"])
        and not app.debug
        and not app.testing
    ):
        app.logger.warning(
            "Rate limits use in-memory storage; set RATELIMIT_STORAGE_URI to a "
            "shared backend in production so limits span workers and restarts."
        )

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(applications_bp)

    return app
