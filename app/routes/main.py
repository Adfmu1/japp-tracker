from flask import Blueprint, Response, redirect, render_template, url_for
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from ..models import db

bp = Blueprint("main", __name__)


@bp.get("/healthz")
def healthz() -> Response:
    return Response("200 OK", status=200, mimetype="text/plain")


@bp.get("/readyz")
def readyz() -> Response:
    try:
        db.session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        db.session.rollback()
        return Response("database unavailable", status=503, mimetype="text/plain")

    return Response("ready", status=200, mimetype="text/plain")


@bp.get("/")
def index() -> str:
    return render_template("index.html")


@bp.get("/index")
def index_alias() -> Response:
    return redirect(url_for("main.index"), code=301)
