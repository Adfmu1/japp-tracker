from typing import Final

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
from flask_wtf import FlaskForm
from sqlalchemy.exc import IntegrityError

from ..forms import ChangeEmailForm, ChangePasswordForm, ChangeUsernameForm
from ..models import db

bp = Blueprint("account", __name__)

# Maps the URL field to (form class, heading, editable attribute).
# A None attribute marks the password form, which has no single value field.
FIELDS: Final[dict[str, tuple[type[FlaskForm], str, str | None]]] = {
    "username": (ChangeUsernameForm, "Change username", "username"),
    "email": (ChangeEmailForm, "Change email", "email"),
    "password": (ChangePasswordForm, "Change password", None),
}


def _render_edit(field: str, heading: str, form: FlaskForm) -> str:
    return render_template(
        "account_edit.html",
        form=form,
        field=field,
        heading=heading,
    )


@bp.get("/account")
@login_required
def index() -> str:
    return render_template("account.html")


@bp.route("/account/edit/<field>", methods=["GET", "POST"])
@login_required
def edit(field: str) -> str | Response:
    config = FIELDS.get(field)
    if config is None:
        abort(404)

    form_class, heading, value_attr = config
    form = form_class()

    if form.is_submitted():
        if not form.validate():
            return _render_edit(field, heading, form)

        if value_attr is None:
            confirmation = form.current_password.data
        else:
            confirmation = form.password.data

        if not current_user.check_password(confirmation):
            flash("Incorrect password.", "error")
            return _render_edit(field, heading, form)

        if value_attr is None:
            if current_user.check_password(form.password.data):
                flash(
                    "New password must be different from the current one.",
                    "error",
                )
                return _render_edit(field, heading, form)
            current_user.set_password(form.password.data)
        else:
            new_value = getattr(form, value_attr).data.strip()
            if field == "email":
                new_value = new_value.lower()
            if new_value == getattr(current_user, value_attr):
                flash(f"Your {field} was not changed.", "info")
                return redirect(url_for("account.index"))
            setattr(current_user, value_attr, new_value)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            current_app.logger.warning(
                "Account update conflict for field %r",
                field,
                exc_info=True,
            )
            if value_attr is None:
                flash("Could not update your password. Please try again.", "error")
            else:
                flash(f"That {field} is already in use.", "error")
            return _render_edit(field, heading, form)

        flash(f"{field.capitalize()} updated.", "success")
        return redirect(url_for("account.index"))

    if value_attr is not None:
        getattr(form, value_attr).data = getattr(current_user, value_attr)

    return _render_edit(field, heading, form)
