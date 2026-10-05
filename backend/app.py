"""LifeGraph Flask application and page/API entry points."""

from flask import Flask, abort, current_app, jsonify, send_from_directory
from werkzeug.exceptions import RequestEntityTooLarge

from config import Config
from database.db import initialize_database
from routes.documents import documents_api
from routes.services import services_api


def create_app():
    app = Flask(
        __name__,
        static_folder=str(Config.FRONTEND_DIR),
        static_url_path="/static",
    )
    app.config.from_object(Config)

    initialize_database(app.config["DATABASE_PATH"])
    app.register_blueprint(services_api)
    app.register_blueprint(documents_api)

    @app.errorhandler(RequestEntityTooLarge)
    def request_too_large(error):
        current_app.logger.warning("Rejected oversized request: %s", error.name)
        return jsonify({"error": "The file exceeds the 10 MB upload limit."}), 413

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
