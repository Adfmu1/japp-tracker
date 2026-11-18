import uuid
from dataclasses import dataclass

from flask import Flask, Response, flash, redirect, render_template, url_for
from flask_login import LoginManager, current_user, login_required, login_user
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from sqlalchemy.exc import IntegrityError

from .config import Config
from .forms import RegistrationForm
from .models import User, db

login_manager = LoginManager()
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id: str):
    try:
        return db.session.get(User, uuid.UUID(user_id))
    except (ValueError, TypeError):
        return None


@dataclass
class JobApplication:
    id: int
    name: str
    description: str
    salary_min: int
    salary_max: int
    stage: str


DUMMY_APPLICATIONS = [
    JobApplication(
        id=1,
        name="Acme Corp",
        description="Backend developer role",
        salary_min=4000,
        salary_max=6000,
        stage="1. Sent application",
    ),
    JobApplication(
        id=2,
        name="Globex",
        description="Python developer",
        salary_min=5000,
        salary_max=7500,
        stage="2. Meeting with X Tuesday 5 pm",
    ),
    JobApplication(
        id=3,
        name="Initech",
        description="Junior backend role",
        salary_min=3000,
        salary_max=4500,
        stage="1. Sent application",
    ),
]


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    Migrate(app, db)
    csrf.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login"

    @app.get("/healthz")
    def healthz():
        return Response("200 OK", status=200, mimetype="text/plain")

    @app.get("/")
    @app.get("/index")
    def index():
        return render_template("index.html")

    @app.get("/applications")
    @login_required
    def applications():
        return render_template(
            "applications.html",
            applications=DUMMY_APPLICATIONS,
        )

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("index"))

        form = RegistrationForm()
        if form.validate_on_submit():
            username = form.username.data.strip()
            email = form.email.data.strip().lower()

            if db.session.execute(
                db.select(User).filter_by(username=username)
            ).scalar_one_or_none():
                form.username.errors.append("Username already taken.")
            elif db.session.execute(
                db.select(User).filter_by(email=email)
            ).scalar_one_or_none():
                form.email.errors.append("Email already registered.")
            else:
                user = User(username=username, email=email)
                user.set_password(form.password.data)
                db.session.add(user)
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    flash("Username or email already in use.", "error")
                else:
                    login_user(user)
                    flash("Registration successful.", "success")
                    return redirect(url_for("applications"))

        return render_template("register.html", form=form)

    return app
