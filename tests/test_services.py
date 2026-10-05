"""Focused tests for the initial service catalogue API."""

import os
import re
import sqlite3
import tempfile
import unittest

from app import create_app


class ServiceCatalogueTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(self.temp_dir.name, "test.db")
        self.app = create_app()
        self.app.config.update(TESTING=True, DATABASE_PATH=database_path)
        from database.db import initialize_database

        initialize_database(database_path)
        self.client = self.app.test_client()
        signup = self.client.get("/signup")
        token = re.search(
            r'name="csrf_token" value="([^"]+)"',
            signup.get_data(as_text=True),
        ).group(1)
        self.client.post(
            "/signup",
            data={
                "csrf_token": token,
                "full_name": "Catalogue Tester",
                "email": f"catalogue-{id(self)}@example.com",
                "password": "correct horse battery staple",
                "confirm_password": "correct horse battery staple",
            },
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_catalogue_has_unverified_certificate_services(self):
        response = self.client.get("/api/services")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["count"], 33)
        self.assertEqual(
            {service["name"] for service in payload["services"]},
            {
                "Residence Certificate",
                "Income Certificate",
                "Community Certificate",
                "Nativity Certificate",
                "First Graduate Certificate",
                "Deserted Woman Certificate",
                "Agricultural Income Certificate",
                "Family Migration Certificate",
                "Unemployment Certificate",
                "Widow Certificate",
                "Legal Heir Certificate",
                "Other Backward Class (OBC) Certificate",
                "Small / Marginal Farmer Certificate",
                "Solvency Certificate",
                "No Male Child Certificate",
                "Unmarried Certificate",
                "Driving Licence — Learner's Licence",
                "Driving Licence — New Driving Licence",
                "Driving Licence — Renewal",
                "Driving Licence — Duplicate",
                "PAN Card — New PAN",
                "PAN Card — Correction",
                "Voter ID — New Registration",
                "Voter ID — Correction",
                "Voter ID — Replacement",
                "Passport — Fresh Passport",
                "Passport — Reissue",
                "Birth Certificate Information",
                "Death Certificate Information",
                "Marriage Certificate Information",
                "Ration Card Services",
                "Aadhaar Update Guidance",
                "Vehicle RC Registration and Related Services",
            },
        )
        for service in payload["services"]:
            self.assertEqual(service["requirements"], [])
            self.assertEqual(service["verification_status"], "needs_verification")
            self.assertIsNone(service["last_verified"])
            self.assertTrue(service["is_demo"])
            self.assertTrue(service["category"])
            self.assertTrue(service["description"])
            self.assertTrue(service["responsible_authority"])
            self.assertTrue(service["official_portal_url"].startswith("https://"))
            self.assertEqual(
                service["requirement_verification_status"],
                "needs_verification",
            )
            if service["category"] == "Tamil Nadu e-Sevai Certificates":
                self.assertEqual(
                    service["source_url"],
                    "https://tnesevai.tn.gov.in/Pages/EsevaiServiceList.aspx",
                )

    def test_search_is_case_insensitive_and_bounded(self):
        response = self.client.get("/api/services?q=income")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["count"], 4)
        self.assertEqual(
            {service["name"] for service in response.get_json()["services"]},
            {
                "Income Certificate",
                "Agricultural Income Certificate",
                "PAN Card — New PAN",
                "PAN Card — Correction",
            },
        )
        self.assertEqual(
            self.client.get(f"/api/services?q={'x' * 101}").status_code,
            400,
        )

    def test_seeding_adds_new_catalogue_entries_and_refreshes_only_legacy_source(self):
        legacy_path = os.path.join(self.temp_dir.name, "legacy.db")
        old_source = "https://www.tnesevai.tn.gov.in/Pages/ServiceList.aspx"
        with sqlite3.connect(legacy_path) as connection:
            connection.execute(
                """
                CREATE TABLE services (
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
            connection.execute(
                """
                INSERT INTO services (
                    id, name, purpose, requirements_json, source_url,
                    verification_status, last_verified, is_demo
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "tn-residence-certificate",
                    "Residence Certificate",
                    "Existing purpose",
                    "[]",
                    old_source,
                    "needs_verification",
                    None,
                    1,
                ),
            )
            connection.execute(
                """
                INSERT INTO services (
                    id, name, purpose, requirements_json, source_url,
                    verification_status, last_verified, is_demo
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "tn-income-certificate",
                    "Income Certificate",
                    "Existing verified description",
                    '["Existing verified proof item"]',
                    old_source,
                    "verified",
                    "2025-01-01",
                    0,
                ),
            )
        connection.close()

        from database.db import initialize_database

        initialize_database(legacy_path)
        self.app.config["DATABASE_PATH"] = legacy_path
        self.client = self.app.test_client()
        signup = self.client.get("/signup")
        token = re.search(
            r'name="csrf_token" value="([^"]+)"',
            signup.get_data(as_text=True),
        ).group(1)
        self.client.post(
            "/signup",
            data={
                "csrf_token": token,
                "full_name": "Legacy Catalogue Tester",
                "email": "legacy-catalogue@example.com",
                "password": "correct horse battery staple",
                "confirm_password": "correct horse battery staple",
            },
        )
        response = self.client.get("/api/services/tn-residence-certificate")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json()["source_url"],
            "https://tnesevai.tn.gov.in/Pages/EsevaiServiceList.aspx",
        )
        self.assertEqual(response.get_json()["purpose"], "Existing purpose")
        preserved = self.client.get("/api/services/tn-income-certificate")
        self.assertEqual(preserved.status_code, 200)
        self.assertEqual(
            preserved.get_json()["purpose"],
            "Existing verified description",
        )
        self.assertEqual(
            preserved.get_json()["requirements"],
            ["Existing verified proof item"],
        )
        self.assertEqual(
            preserved.get_json()["verification_status"],
            "verified",
        )
        self.assertEqual(preserved.get_json()["source_url"], old_source)
        self.assertEqual(self.client.get("/api/services").get_json()["count"], 33)

    def test_service_and_checklist_routes_validate_ids(self):
        detail = self.client.get("/api/services/tn-residence-certificate")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.get_json()["source_url"], "https://tnesevai.tn.gov.in/Pages/EsevaiServiceList.aspx")

        checklist = self.client.get("/api/services/tn-residence-certificate/checklist")
        self.assertEqual(checklist.status_code, 200)
        self.assertEqual(checklist.get_json()["requirements"], [])
        self.assertIn("Needs verification", checklist.get_json()["message"])
        self.assertEqual(self.client.get("/api/services/not-found").status_code, 404)
        self.assertEqual(self.client.get("/api/services/!!").status_code, 400)

    def test_each_demo_service_has_selectable_detail_and_unverified_checklist(self):
        services = self.client.get("/api/services").get_json()["services"]
        for service in services:
            with self.subTest(service=service["id"]):
                detail = self.client.get(f"/api/services/{service['id']}")
                checklist = self.client.get(f"/api/services/{service['id']}/checklist")
                self.assertEqual(detail.status_code, 200)
                self.assertEqual(detail.get_json()["verification_status"], "needs_verification")
                self.assertEqual(detail.get_json()["requirements"], [])
                self.assertEqual(checklist.status_code, 200)
                self.assertEqual(checklist.get_json()["service_id"], service["id"])
                self.assertEqual(checklist.get_json()["requirements"], [])
                self.assertEqual(
                    checklist.get_json()["official_portal_url"],
                    service["official_portal_url"],
                )

    def test_everyday_services_are_separate_and_have_correct_sources(self):
        services = self.client.get("/api/services").get_json()["services"]
        everyday = [
            service for service in services
            if service["category"] == "Everyday Government Services"
        ]
        self.assertEqual(len(everyday), 17)
        self.assertEqual(len({service["id"] for service in services}), 33)
        self.assertEqual(len({service["name"] for service in services}), 33)

        source_by_id = {
            "in-driving-licence-learners": "https://parivahan.gov.in/",
            "in-pan-new": "https://www.incometaxindia.gov.in/en/pan",
            "in-voter-registration": "https://voters.eci.gov.in/",
            "in-passport-fresh": "https://www.passportindia.gov.in/",
        }
        for service_id, expected_source in source_by_id.items():
            with self.subTest(service=service_id):
                response = self.client.get(
                    f"/api/services/{service_id}/checklist"
                )
                self.assertEqual(response.status_code, 200)
                payload = response.get_json()
                self.assertEqual(payload["official_portal_url"], expected_source)
                self.assertEqual(payload["requirements"], [])
                self.assertEqual(
                    payload["requirement_verification_status"],
                    "needs_verification",
                )

    def test_pages_include_workflow_mounts(self):
        service_page = self.client.get("/service")
        checklist_page = self.client.get("/checklist")
        self.assertEqual(service_page.status_code, 200)
        self.assertIn(b"data-service-app", service_page.data)
        self.assertEqual(checklist_page.status_code, 200)
        self.assertIn(b"data-checklist-app", checklist_page.data)
        service_page.close()
        checklist_page.close()

    def test_api_does_not_enable_wildcard_cross_origin_access(self):
        response = self.client.get("/api/services")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Access-Control-Allow-Origin", response.headers)


if __name__ == "__main__":
    unittest.main()