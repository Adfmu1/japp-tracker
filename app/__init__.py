import uuid

from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf import CSRFProtect

from .config import Config
from .models import User, db
from .routes.account import bp as account_bp
from .routes.applications import bp as applications_bp
from .routes.auth import bp as auth_bp
from .routes.main import bp as main_bp

login_manager = LoginManager()
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id: str):
    try:
        return db.session.get(User, uuid.UUID(user_id))
    except (ValueError, TypeError):
        return None


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    Migrate(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(applications_bp)

    return app
