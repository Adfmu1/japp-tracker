from flask import Blueprint, render_template
from flask_login import current_user, login_required

from ..models import JobApplication, db

bp = Blueprint("applications", __name__)


@bp.get("/applications")
@login_required
def index():
    applications = (
        db.session.execute(
            db.select(JobApplication)
            .filter_by(user_id=current_user.id)
            .order_by(JobApplication.created_at.desc())
        )
        .scalars()
        .all()
    )
    return render_template("applications.html", applications=applications)
