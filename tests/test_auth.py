"""Authentication, CSRF, migration, and per-user isolation tests."""

import glob
import io
import os
import re
import sqlite3
import tempfile
import unittest
from contextlib import closing
from unittest.mock import patch

from argon2 import extract_parameters
from app import create_app
from database.db import initialize_database


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = os.path.join(self.temp_dir.name, "lifegraph.db")
        self.upload_directory = os.path.join(self.temp_dir.name, "private-files")
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            DATABASE_PATH=self.database_path,
            UPLOAD_DIRECTORY=self.upload_directory,
            WTF_CSRF_ENABLED=True,
            RATELIMIT_STORAGE_URI="memory://",
        )
        initialize_database(self.database_path)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _csrf(self, client, path="/login"):
        response = client.get(path)
        match = re.search(
            r'(?:name="csrf_token" value="|name="csrf-token" content=")([^"]+)',
            response.get_data(as_text=True),
        )
        self.assertIsNotNone(match)
        return match.group(1)

    def _signup(self, client, email, full_name="Test Person", password="correct horse battery staple"):
        token = self._csrf(client, "/signup")
        return client.post(
            "/signup",
            data={
                "csrf_token": token,
                "full_name": full_name,
                "email": email,
                "password": password,
                "confirm_password": password,
            },
            follow_redirects=False,
        )

    def _login(self, client, email, password):
        token = self._csrf(client)
        return client.post(
            "/login",
            data={"csrf_token": token, "email": email, "password": password},
            follow_redirects=False,
        )

    def _upload(self, client, filename, content):
        token = self._csrf(client, "/dashboard")
        return client.post(
            "/api/documents/upload",
            data={"document": (io.BytesIO(content), filename)},
            headers={"X-CSRFToken": token},
            content_type="multipart/form-data",
        )

    def test_signup_hashes_password_and_rejects_duplicate_email(self):
        response = self._signup(self.client, "Person@example.com")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/dashboard")
        cookie = response.headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)

        with closing(sqlite3.connect(self.database_path)) as connection:
            password_hash = connection.execute(
                "SELECT password_hash FROM users"
            ).fetchone()[0]
        self.assertTrue(password_hash.startswith("$argon2id$"))
        self.assertEqual(extract_parameters(password_hash).type.name, "ID")

        duplicate_client = self.app.test_client()
        duplicate = self._signup(
            duplicate_client,
            "person@EXAMPLE.com",
            full_name="Duplicate",
        )
        self.assertEqual(duplicate.status_code, 409)
        self.assertIn(b"already exists", duplicate.data)

    def test_signup_rejects_invalid_server_side_inputs(self):
        token = self._csrf(self.client, "/signup")
        invalid_forms = (
            {
                "full_name": "",
                "email": "person@example.com",
                "password": "correct horse battery staple",
                "confirm_password": "correct horse battery staple",
            },
            {
                "full_name": "Person",
                "email": "not-an-email",
                "password": "correct horse battery staple",
                "confirm_password": "correct horse battery staple",
            },
            {
                "full_name": "Person",
                "email": "person@example.com",
                "password": "too short",
                "confirm_password": "too short",
            },
            {
                "full_name": "Person",
                "email": "person@example.com",
                "password": "correct horse battery staple",
                "confirm_password": "different secure password",
            },
        )
        for form in invalid_forms:
            with self.subTest(form=form):
                response = self.client.post("/signup", data={"csrf_token": token, **form})
                self.assertEqual(response.status_code, 400)
        with closing(sqlite3.connect(self.database_path)) as connection:
            self.assertEqual(connection.execute("SELECT count(*) FROM users").fetchone()[0], 0)

    def test_invalid_login_logout_and_private_page_redirects(self):
        self._signup(self.client, "person@example.com")
        self.client.post(
            "/logout",
            data={"csrf_token": self._csrf(self.client, "/dashboard")},
        )
        invalid = self._login(self.client, "person@example.com", "incorrect")
        self.assertEqual(invalid.status_code, 401)
        self.assertIn(b"Invalid email or password", invalid.data)

        for path in ("/dashboard", "/checklist", "/static/dashboard.html", "/static/checklist.html"):
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 302)
                self.assertIn("/login", response.headers["Location"])

        self.assertEqual(self.client.get("/service").status_code, 200)
        self.assertEqual(self.client.get("/api/services").status_code, 200)
        self.assertEqual(self.client.get("/static/dashboard.html").status_code, 302)
        self._login(self.client, "person@example.com", "correct horse battery staple")
        dashboard = self.client.get("/dashboard")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"Test Person", dashboard.data)
        token = self._csrf(self.client, "/dashboard")
        logout = self.client.post("/logout", data={"csrf_token": token})
        self.assertEqual(logout.status_code, 302)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)

    def test_login_is_rate_limited(self):
        for attempt in range(5):
            response = self._login(
                self.client,
                "nobody@example.com",
                f"incorrect-{attempt}",
            )
            self.assertEqual(response.status_code, 401)
        blocked = self._login(self.client, "nobody@example.com", "incorrect")
        self.assertEqual(blocked.status_code, 429)

    def test_csrf_is_required_for_authenticated_state_changes(self):
        self._signup(self.client, "csrf@example.com")
        rejected = self.client.post(
            "/api/documents/upload",
            data={"document": (io.BytesIO(b"%PDF-1.7 sample"), "sample.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(rejected.status_code, 400)
        self.assertFalse(os.path.exists(self.upload_directory))

    def test_documents_and_checklist_progress_are_isolated_between_users(self):
        alice = self.app.test_client()
        bob = self.app.test_client()
        self._signup(alice, "alice@example.com", "Alice")
        self._signup(bob, "bob@example.com", "Bob")

        alice_upload = self._upload(alice, "alice.pdf", b"%PDF-1.7 alice")
        bob_upload = self._upload(bob, "bob.pdf", b"%PDF-1.7 bob")
        self.assertEqual(alice_upload.status_code, 201)
        self.assertEqual(bob_upload.status_code, 201)
        alice_document = alice_upload.get_json()
        bob_document = bob_upload.get_json()
        self.assertNotEqual(alice_document["id"], bob_document["id"])
        self.assertEqual(
            [item["filename"] for item in alice.get("/api/documents").get_json()["documents"]],
            ["alice.pdf"],
        )
        self.assertEqual(
            [item["filename"] for item in bob.get("/api/documents").get_json()["documents"]],
            ["bob.pdf"],
        )

        alice_file = alice.get(f"/api/documents/{alice_document['id']}")
        self.assertEqual(alice_file.status_code, 200)
        self.assertEqual(alice_file.data, b"%PDF-1.7 alice")
        alice_file.close()
        self.assertEqual(
            bob.get(f"/api/documents/{alice_document['id']}").status_code,
            404,
        )
        self.assertEqual(
            bob.delete(
                f"/api/documents/{alice_document['id']}",
                headers={"X-CSRFToken": self._csrf(bob, "/dashboard")},
            ).status_code,
            404,
        )
        owner_can_still_read = alice.get(f"/api/documents/{alice_document['id']}")
        self.assertEqual(owner_can_still_read.status_code, 200)
        owner_can_still_read.close()

        service_id = "tn-residence-certificate"
        progress_path = f"/api/checklists/{service_id}"
        self.assertEqual(
            alice.get(progress_path).get_json()["reminders"],
            [False, False],
        )
        update_token = self._csrf(alice, "/checklist")
        updated = alice.put(
            progress_path,
            json={
                "kind": "reminder",
                "index": 0,
                "checked": True,
                "user_id": bob.get("/api/auth/me").get_json()["email"],
            },
            headers={"X-CSRFToken": update_token},
        )
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(alice.get(progress_path).get_json()["reminders"], [True, False])
        self.assertEqual(bob.get(progress_path).get_json()["reminders"], [False, False])
        malformed = alice.put(
            progress_path,
            json={"kind": {}, "index": 0, "checked": True},
            headers={"X-CSRFToken": update_token},
        )
        self.assertEqual(malformed.status_code, 400)

        self.assertEqual(
            alice.delete(
                f"/api/documents/{alice_document['id']}",
                headers={"X-CSRFToken": self._csrf(alice, "/dashboard")},
            ).status_code,
            200,
        )
        self.assertEqual(alice.get(f"/api/documents/{alice_document['id']}").status_code, 404)

    def test_password_reset_uses_one_time_email_token_and_revokes_sessions(self):
        self.app.config.update(
            MAIL_SERVER="smtp.example.test",
            MAIL_PORT=587,
            MAIL_DEFAULT_SENDER="noreply@example.test",
            PUBLIC_BASE_URL="https://lifegraph.example.test",
        )
        self._signup(self.client, "reset@example.com")
        with patch("routes.auth.smtplib.SMTP") as smtp:
            response = self.client.post(
                "/forgot-password",
                data={
                    "csrf_token": self._csrf(self.client, "/forgot-password"),
                    "email": "reset@example.com",
                },
            )
        self.assertEqual(response.status_code, 302)
        body = smtp.return_value.__enter__.return_value.send_message.call_args.args[0].get_content()
        token_match = re.search(r"/reset-password/([A-Za-z0-9_-]+)", body)
        self.assertIsNotNone(token_match)
        token = token_match.group(1)
        reset_path = f"/reset-password/{token}"
        reset_page = self.client.get(reset_path)
        self.assertEqual(reset_page.status_code, 200)
        response = self.client.post(
            reset_path,
            data={
                "csrf_token": self._csrf(self.client, reset_path),
                "password": "a brand new secure password",
                "confirm_password": "a brand new secure password",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get("/dashboard").status_code, 302)
        self.assertEqual(self._login(self.client, "reset@example.com", "correct horse battery staple").status_code, 401)
        self.assertEqual(self._login(self.client, "reset@example.com", "a brand new secure password").status_code, 302)
        self.assertEqual(self.client.get(reset_path).status_code, 400)

    def test_database_migration_creates_a_prechange_backup(self):
        legacy_path = os.path.join(self.temp_dir.name, "legacy.db")
        with closing(sqlite3.connect(legacy_path)) as connection:
            with connection:
                connection.execute("CREATE TABLE legacy_data (value TEXT)")
                connection.execute("INSERT INTO legacy_data VALUES ('preserved')")
        initialize_database(legacy_path)
        backups = glob.glob(f"{legacy_path}.pre-auth-*.bak")
        self.assertEqual(len(backups), 1)
        with closing(sqlite3.connect(backups[0])) as backup:
            self.assertEqual(
                backup.execute("SELECT value FROM legacy_data").fetchone()[0],
                "preserved",
            )
        with closing(sqlite3.connect(legacy_path)) as migrated:
            self.assertEqual(migrated.execute("SELECT value FROM legacy_data").fetchone()[0], "preserved")
            self.assertIsNotNone(
                migrated.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
                ).fetchone()
            )


if __name__ == "__main__":
    unittest.main()
