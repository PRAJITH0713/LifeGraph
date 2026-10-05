"""Tests for private, constrained document uploads."""

import io
import os
import tempfile
import unittest

from app import create_app


class DocumentUploadTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.app = create_app()
        self.upload_directory = os.path.join(self.temp_dir.name, "uploads")
        self.app.config.update(
            TESTING=True,
            UPLOAD_DIRECTORY=self.upload_directory,
        )
        self.client = self.app.test_client()
        self.max_upload_size = self.app.config["MAX_UPLOAD_SIZE_BYTES"]

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_accepts_supported_formats_and_stores_them_privately(self):
        examples = (
            ("sample.pdf", b"%PDF-1.7 sample"),
            ("sample.png", b"\x89PNG\r\n\x1a\nsample"),
            ("sample.jpg", b"\xff\xd8\xffsample"),
            ("sample.jpeg", b"\xff\xd8\xffsample"),
            ("ஆவணம்.pdf", b"%PDF-1.7 Tamil filename"),
        )

        for filename, contents in examples:
            with self.subTest(filename=filename):
                response = self.client.post(
                    "/api/documents/upload",
                    data={"document": (io.BytesIO(contents), filename)},
                    content_type="multipart/form-data",
                )
                self.assertEqual(response.status_code, 201)
                result = response.get_json()
                self.assertEqual(result["filename"], filename)
                self.assertIn("No text extraction", result["message"])
                stored_files = os.listdir(self.upload_directory)
                self.assertEqual(len(stored_files), 1)
                with open(os.path.join(self.upload_directory, stored_files[0]), "rb") as stored_file:
                    self.assertEqual(stored_file.read(), contents)
                self.assertEqual(
                    self.client.get(f"/uploads/{stored_files[0]}").status_code,
                    404,
                )
                os.remove(os.path.join(self.upload_directory, stored_files[0]))

    def test_rejects_unsupported_or_mislabelled_file_types(self):
        for filename, contents in (
            ("notes.txt", b"%PDF-1.7"),
            ("fake.pdf", b"not a PDF"),
        ):
            with self.subTest(filename=filename):
                response = self.client.post(
                    "/api/documents/upload",
                    data={"document": (io.BytesIO(contents), filename)},
                    content_type="multipart/form-data",
                )
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.get_json())
        self.assertFalse(os.path.exists(self.upload_directory))

    def test_rejects_oversized_empty_and_missing_uploads(self):
        oversized = b"%PDF-" + b"x" * self.max_upload_size
        response = self.client.post(
            "/api/documents/upload",
            data={"document": (io.BytesIO(oversized), "large.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("10 MB", response.get_json()["error"])

        empty_response = self.client.post(
            "/api/documents/upload",
            data={"document": (io.BytesIO(b""), "empty.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(empty_response.status_code, 400)
        self.assertEqual(self.client.post("/api/documents/upload").status_code, 400)


if __name__ == "__main__":
    unittest.main()
