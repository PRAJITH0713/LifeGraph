"""SQLite connection and initialization helpers."""

import sqlite3
from contextlib import closing
from pathlib import Path

from database.seed import seed_services


def initialize_database(database_path):
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as connection, connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS services (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                purpose TEXT NOT NULL,
                requirements_json TEXT NOT NULL,
                source_url TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                last_verified TEXT,
                is_demo INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        seed_services(connection)
