import uuid

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError

from ..forms import DeleteApplicationForm, JobApplicationForm
from ..models import JobApplication, db

bp = Blueprint("applications", __name__)


@bp.get("/applications")
@login_required
def index() -> str:
    applications = (
        db.session.execute(
            db.select(JobApplication)
            .filter_by(user_id=current_user.id)
            .order_by(JobApplication.created_at.desc())
        )
        .scalars()
        .all()
    )
    return render_template(
        "applications.html",
        applications=applications,
        delete_form=DeleteApplicationForm(),
    )


@bp.route("/applications/new", methods=["GET", "POST"])
@login_required
def create() -> str | Response:
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
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            current_app.logger.warning(
                "Failed to create a job application",
                exc_info=True,
            )
            flash("Could not save the application. Please try again.", "error")
        else:
            flash("Application added.", "success")
            return redirect(url_for("applications.index"))

    return render_template(
        "application_form.html",
        form=form,
        is_edit=False,
    )


def _get_owned_application(application_id: uuid.UUID) -> JobApplication:
    application = db.session.execute(
        db.select(JobApplication).filter_by(
            id=application_id,
            user_id=current_user.id,
        )
    ).scalar_one_or_none()
    if application is None:
        abort(404)
    return application


@bp.route("/applications/<uuid:application_id>/edit", methods=["GET", "POST"])
@login_required
def edit(application_id: uuid.UUID) -> str | Response:
    application = _get_owned_application(application_id)
    form = JobApplicationForm(obj=application)
    form.submit.label.text = "Save changes"

    if form.validate_on_submit():
        application.name = form.name.data.strip()
        application.company = form.company.data.strip()
        application.description = (form.description.data or "").strip()
        application.salary_min = form.salary_min.data
        application.salary_max = form.salary_max.data
        application.stage = form.stage.data.strip()
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            current_app.logger.warning(
                "Failed to update a job application",
                exc_info=True,
            )
            flash("Could not save the application. Please try again.", "error")
        else:
            flash("Application updated.", "success")
            return redirect(url_for("applications.index"))

    return render_template(
        "application_form.html",
        form=form,
        is_edit=True,
    )


@bp.post("/applications/<uuid:application_id>/delete")
@login_required
def delete(application_id: uuid.UUID) -> Response:
    application = _get_owned_application(application_id)
    db.session.delete(application)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        current_app.logger.warning(
            "Failed to delete a job application",
            exc_info=True,
        )
        flash("Could not delete the application. Please try again.", "error")
    else:
        flash("Application deleted.", "success")
    return redirect(url_for("applications.index"))
