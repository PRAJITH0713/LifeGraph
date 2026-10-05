"""Owner-scoped checklist progress endpoints."""

import re

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user, login_required

from database.db import get_connection
from services.catalogue_service import get_service


checklists_api = Blueprint("checklists_api", __name__, url_prefix="/api/checklists")
SERVICE_ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
REMINDER_COUNT = 2


@checklists_api.get("/<service_id>")
@login_required
def get_progress(service_id):
    if len(service_id) > 80 or not SERVICE_ID_PATTERN.fullmatch(service_id):
        return jsonify({"error": "Invalid service identifier."}), 400
    service = get_service(current_app.config["DATABASE_PATH"], service_id)
    if service is None:
        return jsonify({"error": "Service not found."}), 404
    with get_connection(current_app.config["DATABASE_PATH"]) as connection:
        rows = connection.execute(
            """
            SELECT kind, item_index, checked
            FROM checklist_progress
            WHERE user_id = ? AND service_id = ?
            """,
            (current_user.get_id(), service_id),
        ).fetchall()
    requirements = [False] * len(service["requirements"])
    reminders = [False] * REMINDER_COUNT
    for row in rows:
        target = requirements if row["kind"] == "requirement" else reminders
        if row["item_index"] < len(target):
            target[row["item_index"]] = bool(row["checked"])
    return jsonify(
        {
            "service_id": service_id,
            "requirements": requirements,
            "reminders": reminders,
        }
    )


@checklists_api.put("/<service_id>")
@login_required
def update_progress(service_id):
    if len(service_id) > 80 or not SERVICE_ID_PATTERN.fullmatch(service_id):
        return jsonify({"error": "Invalid service identifier."}), 400
    service = get_service(current_app.config["DATABASE_PATH"], service_id)
    if service is None:
        return jsonify({"error": "Service not found."}), 404
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "A JSON checklist update is required."}), 400
    kind = payload.get("kind")
    if not isinstance(kind, str):
        return jsonify({"error": "Invalid checklist item update."}), 400
    item_index = payload.get("index")
    checked = payload.get("checked")
    count = len(service["requirements"]) if kind == "requirement" else REMINDER_COUNT if kind == "reminder" else 0
    if (
        kind not in {"requirement", "reminder"}
        or isinstance(item_index, bool)
        or not isinstance(item_index, int)
        or item_index < 0
        or item_index >= count
        or not isinstance(checked, bool)
    ):
        return jsonify({"error": "Invalid checklist item update."}), 400

    with get_connection(current_app.config["DATABASE_PATH"]) as connection:
        connection.execute(
            """
            INSERT INTO checklist_progress (user_id, service_id, kind, item_index, checked)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, service_id, kind, item_index)
            DO UPDATE SET checked = excluded.checked
            """,
            (
                current_user.get_id(),
                service_id,
                kind,
                item_index,
                int(checked),
            ),
        )
    return jsonify({"service_id": service_id, "kind": kind, "index": item_index, "checked": checked})
