from flask import Flask, Response, render_template


def create_app():
    app = Flask(__name__)

    @app.get("/healthz")
    def healthz():
        return Response("200 OK", status=200, mimetype="text/plain")

    @app.get("/")
    @app.get("/index")
    def index():
        return render_template("index.html", current_user=True)

    return app
