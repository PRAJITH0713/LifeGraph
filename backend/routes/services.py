"""Read-only API for the service catalogue and its checklist data."""

import re
import sqlite3

from flask import Blueprint, current_app, jsonify, request
from flask_login import login_required

from services.catalogue_service import get_service, list_services
from services.checklist_service import build_checklist

services_api = Blueprint("services_api", __name__, url_prefix="/api/services")
SERVICE_ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


@services_api.get("")
@login_required
def services_index():
	query = request.args.get("q", "").strip()
	if len(query) > 100:
		return jsonify({"error": "Search text must be 100 characters or fewer."}), 400
	try:
		services = list_services(current_app.config["DATABASE_PATH"], query)
	except sqlite3.Error:
		return jsonify({"error": "The service catalogue is temporarily unavailable."}), 503
	return jsonify({"count": len(services), "services": services})


@services_api.get("/<service_id>")
@login_required
def service_detail(service_id):
	if len(service_id) > 80 or not SERVICE_ID_PATTERN.fullmatch(service_id):
		return jsonify({"error": "Invalid service identifier."}), 400
	try:
		service = get_service(current_app.config["DATABASE_PATH"], service_id)
	except sqlite3.Error:
		return jsonify({"error": "The service catalogue is temporarily unavailable."}), 503
	if service is None:
		return jsonify({"error": "Service not found."}), 404
	return jsonify(service)


@services_api.get("/<service_id>/checklist")
@login_required
def service_checklist(service_id):
	if len(service_id) > 80 or not SERVICE_ID_PATTERN.fullmatch(service_id):
		return jsonify({"error": "Invalid service identifier."}), 400
	try:
		service = get_service(current_app.config["DATABASE_PATH"], service_id)
	except sqlite3.Error:
		return jsonify({"error": "The service catalogue is temporarily unavailable."}), 503
	if service is None:
		return jsonify({"error": "Service not found."}), 404
	return jsonify(build_checklist(service))
