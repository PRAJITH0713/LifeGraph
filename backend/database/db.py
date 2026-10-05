"""SQLite connection and initialization helpers."""

import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path

from database.seed import seed_services


@contextmanager
def get_connection(database_path):
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def _backup_before_auth_migration(path):
    if not path.is_file() or path.stat().st_size == 0:
        return

    with closing(sqlite3.connect(path)) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        if not tables or "users" in tables:
            return

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = path.with_name(f"{path.name}.pre-auth-{timestamp}.bak")
        suffix = 1
        while backup_path.exists():
            backup_path = path.with_name(
                f"{path.name}.pre-auth-{timestamp}-{suffix}.bak"
            )
            suffix += 1
        with closing(sqlite3.connect(backup_path)) as backup:
            connection.backup(backup)


def initialize_database(database_path):
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _backup_before_auth_migration(path)
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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                auth_version INTEGER NOT NULL DEFAULT 1,
                reset_token_hash TEXT,
                reset_expires_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                original_filename TEXT NOT NULL,
                stored_filename TEXT NOT NULL UNIQUE,
                size_bytes INTEGER NOT NULL CHECK (size_bytes > 0),
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS documents_by_owner
            ON documents(user_id, created_at DESC)
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS checklist_progress (
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                service_id TEXT NOT NULL REFERENCES services(id) ON DELETE CASCADE,
                kind TEXT NOT NULL CHECK (kind IN ('requirement', 'reminder')),
                item_index INTEGER NOT NULL CHECK (item_index >= 0),
                checked INTEGER NOT NULL CHECK (checked IN (0, 1)),
                PRIMARY KEY (user_id, service_id, kind, item_index)
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
        connection.execute(
            """
            INSERT INTO app_metadata (key, value)
            VALUES ('auth_schema_version', '1')
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """
        )
