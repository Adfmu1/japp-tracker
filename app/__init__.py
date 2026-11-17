from dataclasses import dataclass

from flask import Flask, Response, render_template


@dataclass
class JobApplication:
    id: int
    name: str
    description: str
    salary_min: int
    salary_max: int
    stage: str


DUMMY_APPLICATION = JobApplication(
    id=1,
    name="Acme Corp",
    description="Backend developer role",
    salary_min=4000,
    salary_max=6000,
    stage="1. Sent application",
)


def create_app():
    app = Flask(__name__)

    @app.get("/healthz")
    def healthz():
        return Response("200 OK", status=200, mimetype="text/plain")

    @app.get("/")
    @app.get("/index")
    def index():
        return render_template(
            "index.html",
            current_user=True,
            application=DUMMY_APPLICATION,
        )

    return app
