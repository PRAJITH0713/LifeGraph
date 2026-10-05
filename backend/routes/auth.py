"""Signup, login, logout, and email-based password reset routes."""

import hashlib
import secrets
import smtplib
import sqlite3
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from urllib.parse import urlsplit

from email_validator import EmailNotValidError, validate_email
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required, login_user, logout_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from database.db import get_connection
from models import User, password_hasher, verify_password


auth_api = Blueprint("auth_api", __name__)
limiter = Limiter(key_func=get_remote_address)
_dummy_password_hash = password_hasher.hash(secrets.token_urlsafe(32))


def _utc_now():
    return datetime.now(timezone.utc)


def _valid_redirect_target(target):
    if not target or not target.startswith("/") or target.startswith("//"):
        return False
    return (
        "\\" not in target
        and "\r" not in target
        and "\n" not in target
        and not target.startswith("/%2f")
        and not target.startswith("/%5c")
    )


def _password_error(password):
    if len(password) < 12:
        return "Use a password with at least 12 characters."
    if len(password) > 128:
        return "Passwords must be 128 characters or fewer."
    return None


def _render_auth(mode, error=None, status=200, token=None):
    return (
        render_template(
            "auth.html",
            mode=mode,
            error=error,
            reset_token=token,
        ),
        status,
    )


def _normalized_email(value):
    try:
        return validate_email(
            value.strip(),
            check_deliverability=False,
        ).normalized.lower()
    except (EmailNotValidError, AttributeError):
        return None


def _send_reset_email(email, token):
    config = current_app.config
    required_settings = (
        config.get("MAIL_SERVER"),
        config.get("MAIL_DEFAULT_SENDER"),
        config.get("PUBLIC_BASE_URL"),
    )
    if not all(required_settings):
        current_app.logger.error(
            "Password reset email is not configured; set mail settings and "
            "LIFEGRAPH_PUBLIC_URL."
        )
        return False

    base_url = config["PUBLIC_BASE_URL"].rstrip("/")
    parsed_url = urlsplit(base_url)
    if (
        parsed_url.scheme != "https"
        or not parsed_url.hostname
        or parsed_url.username is not None
        or parsed_url.password is not None
        or parsed_url.query
        or parsed_url.fragment
    ):
        current_app.logger.error("LIFEGRAPH_PUBLIC_URL must be a trusted HTTPS origin.")
        return False

    reset_url = f"{base_url}{url_for('auth_api.reset_password', token=token)}"
    message = EmailMessage()
    message["Subject"] = "Reset your LifeGraph password"
    message["From"] = config["MAIL_DEFAULT_SENDER"]
    message["To"] = email
    message.set_content(
        "A password reset was requested for your LifeGraph account.\n\n"
        f"Reset your password using this link (valid for 30 minutes): {reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )

    try:
        with smtplib.SMTP(config["MAIL_SERVER"], config.get("MAIL_PORT", 587), timeout=10) as mail:
            mail.starttls()
            username = config.get("MAIL_USERNAME")
            password = config.get("MAIL_PASSWORD")
            if username:
                mail.login(username, password or "")
            mail.send_message(message)
    except (OSError, smtplib.SMTPException):
        current_app.logger.exception("Could not send a password reset email.")
        return False
    return True


@auth_api.get("/signup")
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("frontend_page", page="dashboard"))
    return _render_auth("signup")


@auth_api.post("/signup")
@limiter.limit("5 per hour")
def create_account():
    if current_user.is_authenticated:
        return redirect(url_for("frontend_page", page="dashboard"))
    full_name = request.form.get("full_name", "").strip()
    raw_email = request.form.get("email", "")
    email = _normalized_email(raw_email)
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")

    if not full_name or len(full_name) > 100 or any(ord(char) < 32 for char in full_name):
        return _render_auth("signup", "Enter a name of 1 to 100 characters.", 400)
    if email is None or len(email) > 254:
        return _render_auth("signup", "Enter a valid email address.", 400)
    password_error = _password_error(password)
    if password_error:
        return _render_auth("signup", password_error, 400)
    if password != confirm_password:
        return _render_auth("signup", "The passwords do not match.", 400)

    user_id = secrets.token_hex(16)
    try:
        with get_connection(current_app.config["DATABASE_PATH"]) as connection:
            connection.execute(
                """
                INSERT INTO users (id, full_name, email, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    full_name,
                    email,
                    password_hasher.hash(password),
                    _utc_now().isoformat(),
                ),
            )
            row = connection.execute(
                "SELECT id, full_name, email, auth_version FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
    except sqlite3.IntegrityError:
        with get_connection(current_app.config["DATABASE_PATH"]) as connection:
            duplicate = connection.execute(
                "SELECT 1 FROM users WHERE email = ?",
                (email,),
            ).fetchone()
        if duplicate is not None:
            return _render_auth("signup", "An account with that email already exists.", 409)
        current_app.logger.exception("Could not create an account because of a database constraint.")
        return _render_auth("signup", "Account creation is temporarily unavailable.", 503)
    except sqlite3.Error:
        current_app.logger.exception("Could not create an account.")
        return _render_auth("signup", "Account creation is temporarily unavailable.", 503)

    session.clear()
    session.permanent = True
    login_user(User.from_row(row), fresh=True)
    session["auth_version"] = row["auth_version"]
    return redirect(url_for("frontend_page", page="dashboard"))


@auth_api.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("frontend_page", page="dashboard"))
    return _render_auth("login")


@auth_api.post("/login")
@limiter.limit("5 per minute")
def authenticate():
    if current_user.is_authenticated:
        return redirect(url_for("frontend_page", page="dashboard"))
    email = _normalized_email(request.form.get("email", ""))
    password = request.form.get("password", "")
    row = None
    if email is not None:
        with get_connection(current_app.config["DATABASE_PATH"]) as connection:
            row = connection.execute(
                "SELECT id, full_name, email, password_hash, auth_version FROM users WHERE email = ?",
                (email,),
            ).fetchone()
    password_hash = row["password_hash"] if row is not None else _dummy_password_hash
    if len(password) > 128 or not verify_password(password_hash, password) or row is None:
        return _render_auth("login", "Invalid email or password.", 401)

    session.clear()
    session.permanent = True
    login_user(User.from_row(row), fresh=True)
    session["auth_version"] = row["auth_version"]
    target = request.args.get("next")
    return redirect(
        target
        if _valid_redirect_target(target)
        else url_for("frontend_page", page="dashboard")
    )


@auth_api.post("/logout")
@login_required
def logout():
    if current_user.is_authenticated:
        logout_user()
    session.clear()
    return redirect(url_for("auth_api.login"))


@auth_api.get("/forgot-password")
def forgot_password():
    return _render_auth("forgot")


@auth_api.post("/forgot-password")
@limiter.limit("3 per hour")
def request_password_reset():
    email = _normalized_email(request.form.get("email", ""))
    reset_user = None
    token = None
    token_hash = None
    if email is not None:
        with get_connection(current_app.config["DATABASE_PATH"]) as connection:
            reset_user = connection.execute(
                "SELECT id, email FROM users WHERE email = ?",
                (email,),
            ).fetchone()
            if reset_user is not None:
                token = secrets.token_urlsafe(32)
                token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
                expires_at = (_utc_now() + timedelta(minutes=30)).isoformat()
                connection.execute(
                    """
                    UPDATE users
                    SET reset_token_hash = ?, reset_expires_at = ?
                    WHERE id = ?
                    """,
                    (token_hash, expires_at, reset_user["id"]),
                )
    if reset_user is not None and token is not None and token_hash is not None:
        if not _send_reset_email(reset_user["email"], token):
            with get_connection(current_app.config["DATABASE_PATH"]) as connection:
                connection.execute(
                    """
                    UPDATE users
                    SET reset_token_hash = NULL, reset_expires_at = NULL
                    WHERE id = ? AND reset_token_hash = ?
                    """,
                    (reset_user["id"], token_hash),
                )
    flash(
        "If an account matches that email and email delivery is configured, "
        "a password reset link will be sent.",
        "info",
    )
    return redirect(url_for("auth_api.forgot_password"))


@auth_api.get("/reset-password/<token>")
def reset_password(token):
    if len(token) > 128:
        abort(404)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with get_connection(current_app.config["DATABASE_PATH"]) as connection:
        row = connection.execute(
            """
            SELECT id FROM users
            WHERE reset_token_hash = ? AND reset_expires_at > ?
            """,
            (token_hash, _utc_now().isoformat()),
        ).fetchone()
    if row is None:
        return _render_auth(
            "reset",
            "This reset link is invalid or has expired.",
            400,
            token=token,
        )
    return _render_auth("reset", token=token)


@auth_api.post("/reset-password/<token>")
def set_new_password(token):
    if len(token) > 128:
        abort(404)
    password = request.form.get("password", "")
    confirm_password = request.form.get("confirm_password", "")
    password_error = _password_error(password)
    if password_error:
        return _render_auth("reset", password_error, 400, token)
    if password != confirm_password:
        return _render_auth("reset", "The passwords do not match.", 400, token)
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    with get_connection(current_app.config["DATABASE_PATH"]) as connection:
        cursor = connection.execute(
            """
            UPDATE users
            SET password_hash = ?, reset_token_hash = NULL, reset_expires_at = NULL,
                auth_version = auth_version + 1
            WHERE reset_token_hash = ? AND reset_expires_at > ?
            """,
            (
                password_hasher.hash(password),
                token_hash,
                _utc_now().isoformat(),
            ),
        )
        if cursor.rowcount != 1:
            return _render_auth(
                "reset",
                "This reset link is invalid or has expired.",
                400,
                token=token,
            )
    flash("Your password was changed. Please log in.", "success")
    return redirect(url_for("auth_api.login"))


@auth_api.get("/api/auth/me")
@login_required
def current_account():
    return jsonify(
        {
            "authenticated": True,
            "full_name": current_user.full_name,
            "email": current_user.email,
        }
    )
