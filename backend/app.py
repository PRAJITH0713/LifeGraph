"""LifeGraph Flask application and page/API entry points."""

from flask import Flask, abort, current_app, jsonify, redirect, render_template, request, session, url_for
from flask_login import LoginManager, current_user
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError, generate_csrf
from werkzeug.exceptions import RequestEntityTooLarge

from config import Config
from database.db import initialize_database
from models import User
from routes.auth import auth_api, limiter
from routes.checklists import checklists_api
from routes.documents import documents_api
from routes.services import services_api


login_manager = LoginManager()
csrf = CSRFProtect()


def create_app():
    app = Flask(
        __name__,
        static_folder=str(Config.FRONTEND_DIR),
        static_url_path="/static",
        template_folder=str(Config.FRONTEND_DIR),
    )
    app.config.from_object(Config)

    if _is_within(app.config["UPLOAD_DIRECTORY"], app.static_folder):
        raise ValueError("Private document storage must be outside the public static directory.")

    initialize_database(app.config["DATABASE_PATH"])
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = "auth_api.login"
    login_manager.login_message = None
    limiter.init_app(app)
    app.register_blueprint(auth_api)
    app.register_blueprint(services_api)
    app.register_blueprint(checklists_api)
    app.register_blueprint(documents_api)

    @app.context_processor
    def csrf_template_context():
        return {"csrf_token": generate_csrf}

    @login_manager.user_loader
    def load_user(user_id):
        from database.db import get_connection

        with get_connection(current_app.config["DATABASE_PATH"]) as connection:
            row = connection.execute(
                "SELECT id, full_name, email, auth_version FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        if row is None or session_auth_version() != row["auth_version"]:
            return None
        return User.from_row(row)

    @login_manager.unauthorized_handler
    def unauthorized():
        if request_path_is_api():
            return jsonify({"error": "Authentication is required."}), 401
        return redirect(url_for("auth_api.login", next=request_path()))

    @app.errorhandler(RequestEntityTooLarge)
    def request_too_large(error):
        current_app.logger.warning("Rejected oversized request: %s", error.name)
        return jsonify({"error": "The file exceeds the 10 MB upload limit."}), 413

    @app.errorhandler(CSRFError)
    def csrf_rejected(error):
        current_app.logger.warning("Rejected request with invalid CSRF token: %s", request.path)
        if request.path.startswith("/api/"):
            if not current_user.is_authenticated:
                return jsonify({"error": "Authentication is required."}), 401
            return jsonify({"error": "CSRF validation failed. Reload the page and try again."}), 400
        return "The form expired or could not be verified. Go back, reload the page, and try again.", 400

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if (
            request.path in {"/dashboard", "/service", "/checklist"}
            or request.path.startswith(("/api/auth/", "/api/services", "/api/documents", "/api/checklists", "/login", "/signup", "/forgot-password", "/reset-password"))
        ):
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.before_request
    def protect_static_private_pages():
        if request.path.startswith("/static/") and request.path.lower().endswith(".html"):
            if request.path in {"/static/dashboard.html", "/static/checklist.html"}:
                if not current_user.is_authenticated:
                    page = request.path.removeprefix("/static/").removesuffix(".html")
                    return redirect(url_for("auth_api.login", next=f"/{page}"))
                page = request.path.removeprefix("/static/").removesuffix(".html")
                return redirect(f"/{page}")
            abort(404)
        return None

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "application": "LifeGraph"})

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/<page>")
    def frontend_page(page):
        pages = {"dashboard", "service", "checklist", "map"}
        if page not in pages:
            abort(404)
        if page in {"dashboard", "service", "checklist"} and not current_user.is_authenticated:
            return redirect(url_for("auth_api.login", next=request_path()))
        return render_template(f"{page}.html")

    return app


def _is_within(path, parent):
    from pathlib import Path

    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
    except ValueError:
        return False
    return True


def request_path():
    return request.full_path.rstrip("?")


def request_path_is_api():
    return request_path().startswith("/api/")


def session_auth_version():
    return session.get("auth_version")


app = create_app()


if __name__ == "__main__":
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=app.config["DEBUG"])
