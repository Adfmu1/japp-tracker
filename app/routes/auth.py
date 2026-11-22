from urllib.parse import unquote, urljoin, urlsplit

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from ..forms import LoginForm, RegistrationForm
from ..models import User, db, verify_dummy_password

bp = Blueprint("auth", __name__)


def _safe_next(target: str) -> str | None:
    """Return a same-origin URL for target, or None when it is unsafe.

    The decoded value is validated and the normalized URL is returned, so the
    redirect cannot use a different value than the one that was checked.
    """
    if not target.startswith("/") or target.startswith("//"):
        return None
    decoded = unquote(target)
    if "\\" in decoded or any(ord(char) < 0x20 for char in decoded):
        return None
    host = urlsplit(request.host_url)
    candidate = urlsplit(urljoin(request.host_url, target))
    if candidate.scheme not in {"http", "https"} or candidate.netloc != host.netloc:
        return None
    return candidate.geturl()


@bp.route("/login", methods=["GET", "POST"])
def login() -> str | Response:
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(
            db.select(User).filter_by(username=form.username.data.strip())
        ).scalar_one_or_none()

        if user is None:
            # Spend the same time as a real verification to avoid revealing
            # which usernames exist.
            verify_dummy_password(form.password.data)
            flash("Invalid username or password.", "error")
            return render_template("login.html", form=form)

        if not user.check_password(form.password.data):
            flash("Invalid username or password.", "error")
            return render_template("login.html", form=form)

        login_user(user, remember=form.remember.data)
        if db.session.is_modified(user):
            # Persist a password rehash performed by check_password().
            db.session.commit()
        flash("Logged in successfully.", "success")
        next_url = _safe_next(request.args.get("next", ""))
        return redirect(next_url or url_for("applications.index"))

    return render_template("login.html", form=form)


@bp.post("/logout")
@login_required
def logout() -> Response:
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("main.index"))


@bp.route("/register", methods=["GET", "POST"])
def register() -> str | Response:
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

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
                current_app.logger.warning(
                    "Registration conflict for username %r",
                    username,
                    exc_info=True,
                )
                flash("Username or email already in use.", "error")
            else:
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for("auth.login"))

    return render_template("register.html", form=form)
