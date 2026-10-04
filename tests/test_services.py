"""Focused tests for the initial service catalogue API."""

import os
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

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_catalogue_has_unverified_certificate_services(self):
        response = self.client.get("/api/services")
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["count"], 2)
        self.assertEqual(
            {service["name"] for service in payload["services"]},
            {"Residence Certificate", "Income Certificate"},
        )
        for service in payload["services"]:
            self.assertEqual(service["requirements"], [])
            self.assertEqual(service["verification_status"], "needs_verification")
            self.assertIsNone(service["last_verified"])
            self.assertTrue(service["is_demo"])

    def test_search_is_case_insensitive_and_bounded(self):
        response = self.client.get("/api/services?q=income")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["count"], 1)
        self.assertEqual(
            self.client.get(f"/api/services?q={'x' * 101}").status_code,
            400,
        )

    def test_service_and_checklist_routes_validate_ids(self):
        detail = self.client.get("/api/services/tn-residence-certificate")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.get_json()["source_url"], "https://www.tnesevai.tn.gov.in/Pages/ServiceList.aspx")

        checklist = self.client.get("/api/services/tn-residence-certificate/checklist")
        self.assertEqual(checklist.status_code, 200)
        self.assertEqual(checklist.get_json()["requirements"], [])
        self.assertIn("Needs verification", checklist.get_json()["message"])
        self.assertEqual(self.client.get("/api/services/not-found").status_code, 404)
        self.assertEqual(self.client.get("/api/services/!!").status_code, 400)

    def test_pages_include_workflow_mounts(self):
        service_page = self.client.get("/service")
        checklist_page = self.client.get("/checklist")
        self.assertEqual(service_page.status_code, 200)
        self.assertIn(b"data-service-app", service_page.data)
        self.assertEqual(checklist_page.status_code, 200)
        self.assertIn(b"data-checklist-app", checklist_page.data)
        service_page.close()
        checklist_page.close()


if __name__ == "__main__":
    unittest.main()