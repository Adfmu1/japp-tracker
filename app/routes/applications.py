from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from ..forms import JobApplicationForm
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


@bp.route("/applications/new", methods=["GET", "POST"])
@login_required
def create():
    form = JobApplicationForm()
    if form.validate_on_submit():
        application = JobApplication(
            user_id=current_user.id,
            name=form.name.data.strip(),
            company=form.company.data.strip(),
            description=(form.description.data or "").strip(),
            salary_min=form.salary_min.data,
            salary_max=form.salary_max.data,
            stage=form.stage.data.strip(),
        )
        db.session.add(application)
        db.session.commit()
        flash("Application added.", "success")
        return redirect(url_for("applications.index"))

    return render_template("application_form.html", form=form)
