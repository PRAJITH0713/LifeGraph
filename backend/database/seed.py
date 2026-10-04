"""Helpers for reading explicitly marked demo JSON data."""

import json
from pathlib import Path

import sqlite3

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_demo_json(filename):
    with (DATA_DIR / filename).open(encoding="utf-8") as data_file:
        return json.load(data_file)


def seed_services(connection: sqlite3.Connection):
    catalogue = load_demo_json("services.json")
    for service in catalogue["services"]:
        connection.execute(
            """
            INSERT OR IGNORE INTO services (
                id, name, purpose, requirements_json, source_url,
                verification_status, last_verified, is_demo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                service["id"],
                service["name"],
                service["purpose"],
                json.dumps(service["requirements"]),
                service["source_url"],
                service["verification_status"],
                service["last_verified"],
            ),
        )
