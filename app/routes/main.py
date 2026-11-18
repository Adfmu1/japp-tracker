from flask import Blueprint, Response, render_template

bp = Blueprint("main", __name__)


@bp.get("/healthz")
def healthz():
    return Response("200 OK", status=200, mimetype="text/plain")


@bp.get("/")
@bp.get("/index")
def index():
    return render_template("index.html")
