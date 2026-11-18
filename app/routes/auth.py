from urllib.parse import urljoin, urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from ..forms import LoginForm, RegistrationForm
from ..models import User, db

bp = Blueprint("auth", __name__)


def _is_safe_next(target: str) -> bool:
    if not target.startswith("/") or target.startswith("//") or "\\" in target:
        return False
    host = urlsplit(request.host_url)
    candidate = urlsplit(urljoin(request.host_url, target))
    return candidate.scheme in {"http", "https"} and candidate.netloc == host.netloc


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(
            db.select(User).filter_by(username=form.username.data.strip())
        ).scalar_one_or_none()

        if user is None or not user.check_password(form.password.data):
            flash("Invalid username or password.", "error")
            return render_template("login.html", form=form)

        login_user(user, remember=form.remember.data)
        flash("Logged in successfully.", "success")
        next_url = request.args.get("next")
        if next_url and _is_safe_next(next_url):
            return redirect(next_url)
        return redirect(url_for("applications.index"))

    return render_template("login.html", form=form)


@bp.get("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out.", "success")
    return redirect(url_for("main.index"))


@bp.route("/register", methods=["GET", "POST"])
def register():
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
                flash("Username or email already in use.", "error")
            else:
                flash("Registration successful. Please log in.", "success")
                return redirect(url_for("auth.login"))

    return render_template("register.html", form=form)
