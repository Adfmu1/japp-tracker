from dataclasses import dataclass

from flask import Blueprint, render_template
from flask_login import login_required

bp = Blueprint("applications", __name__)


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


@bp.get("/applications")
@login_required
def index():
    return render_template(
        "applications.html",
        applications=DUMMY_APPLICATIONS,
    )
