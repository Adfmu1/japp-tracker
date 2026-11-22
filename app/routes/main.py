from flask import Blueprint, Response, redirect, render_template, url_for

bp = Blueprint("main", __name__)


@bp.get("/healthz")
def healthz() -> Response:
    return Response("200 OK", status=200, mimetype="text/plain")


@bp.get("/")
def index() -> str:
    return render_template("index.html")


@bp.get("/index")
def index_alias() -> Response:
    return redirect(url_for("main.index"), code=301)
