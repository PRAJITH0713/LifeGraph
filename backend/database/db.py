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
                is_demo INTEGER NOT NULL DEFAULT 1,
                category TEXT NOT NULL DEFAULT 'Tamil Nadu e-Sevai Certificates',
                responsible_authority TEXT NOT NULL DEFAULT '',
                requirement_verification_status TEXT NOT NULL DEFAULT 'needs_verification'
            )
            """
        )
        columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(services)").fetchall()
        }
        if "category" not in columns:
            connection.execute(
                "ALTER TABLE services ADD COLUMN category TEXT NOT NULL DEFAULT 'Tamil Nadu e-Sevai Certificates'"
            )
        if "responsible_authority" not in columns:
            connection.execute(
                "ALTER TABLE services ADD COLUMN responsible_authority TEXT NOT NULL DEFAULT ''"
            )
        if "requirement_verification_status" not in columns:
            connection.execute(
                """
                ALTER TABLE services
                ADD COLUMN requirement_verification_status TEXT NOT NULL DEFAULT 'needs_verification'
                """
            )
            connection.execute(
                """
                UPDATE services
                SET requirement_verification_status = verification_status
                """
            )
        seed_services(connection)
