from dataclasses import dataclass

from flask import Flask, Response, render_template
from flask_migrate import Migrate

from .config import Config
from .models import db


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

    @app.get("/healthz")
    def healthz():
        return Response("200 OK", status=200, mimetype="text/plain")

    @app.get("/")
    @app.get("/index")
    def index():
        return render_template("index.html", current_user=True)

    @app.get("/applications")
    def applications():
        return render_template(
            "applications.html",
            current_user=True,
            applications=DUMMY_APPLICATIONS,
        )

    return app
