"""LifeGraph Flask application and page/API entry points."""

from flask import Flask, abort, jsonify, send_from_directory

from config import Config
from database.db import initialize_database

try:
    from flask_cors import CORS
except ImportError:
    CORS = None


def create_app():
    app = Flask(
        __name__,
        static_folder=str(Config.FRONTEND_DIR),
        static_url_path="/static",
    )
    app.config.from_object(Config)

    initialize_database(app.config["DATABASE_PATH"])
    if CORS is not None:
        CORS(app, resources={r"/api/*": {"origins": "*"}})

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "application": "LifeGraph"})

    @app.get("/")
    def index():
        return send_from_directory(Config.FRONTEND_DIR, "index.html")

    @app.get("/<page>")
    def frontend_page(page):
        pages = {"dashboard", "service", "checklist", "map"}
        if page not in pages:
            abort(404)
        return send_from_directory(Config.FRONTEND_DIR, f"{page}.html")

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=app.config["DEBUG"])
