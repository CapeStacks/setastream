import io
import json
import unittest
import zipfile

import httpx2
from docx import Document

from fastapi_test_app.main import MAX_CONFIGURATION_BYTES, app

from .helpers import configuration_bytes, make_docx, make_pdf


class FastApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app),
            base_url="http://testserver",
        )

    async def asyncTearDown(self):
        await self.client.aclose()

    def _common_files(self):
        return {
            "certificate_pdf": ("template.pdf", make_pdf(), "application/pdf"),
            "configuration_json": (
                "configuration.json",
                configuration_bytes(),
                "application/json",
            ),
        }

    def _zip_names(self, response):
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            return archive.namelist()

    def _common_docx_files(self):
        return {
            "certificate_docx": (
                "template.docx",
                make_docx(),
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            "configuration_json": (
                "configuration.json",
                configuration_bytes(),
                "application/json",
            ),
        }

    async def test_health_endpoint(self):
        response = await self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    async def test_csv_endpoint_success(self):
        files = self._common_files()
        files["csv_file"] = (
            "recipients.csv",
            b"recipient_name,certificate_number\nAmina,CERT-001\n",
            "text/csv",
        )

        response = await self.client.post("/generate/csv", files=files)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/zip")
        self.assertEqual(self._zip_names(response), ["CERT-001.pdf"])

    async def test_manual_endpoint_with_one_record(self):
        files = self._common_files()
        files["recipients_json"] = (
            "recipients.json",
            json.dumps(
                [{"recipient_name": "Amina", "certificate_number": "CERT-001"}]
            ).encode(),
            "application/json",
        )

        response = await self.client.post("/generate/manual", files=files)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._zip_names(response), ["CERT-001.pdf"])

    async def test_manual_endpoint_with_two_records(self):
        files = self._common_files()
        files["recipients_json"] = (
            "recipients.json",
            json.dumps(
                [
                    {"recipient_name": "Amina", "certificate_number": "CERT-001"},
                    {"recipient_name": "Naledi", "certificate_number": "CERT-002"},
                ]
            ).encode(),
            "application/json",
        )

        response = await self.client.post("/generate/manual", files=files)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self._zip_names(response), ["CERT-001.pdf", "CERT-002.pdf"]
        )

    async def test_malformed_configuration_returns_4xx(self):
        files = self._common_files()
        files["configuration_json"] = (
            "configuration.json",
            b"{not-json",
            "application/json",
        )
        files["csv_file"] = (
            "recipients.csv",
            b"recipient_name,certificate_number\nAmina,CERT-001\n",
            "text/csv",
        )

        response = await self.client.post("/generate/csv", files=files)

        self.assertEqual(response.status_code, 422)
        self.assertIn("malformed", response.json()["detail"])

    async def test_malformed_manual_json_returns_4xx(self):
        files = self._common_files()
        files["recipients_json"] = (
            "recipients.json",
            b"[not-json",
            "application/json",
        )

        response = await self.client.post("/generate/manual", files=files)

        self.assertEqual(response.status_code, 422)
        self.assertIn("malformed", response.json()["detail"])

    async def test_missing_uploaded_files_return_4xx(self):
        response = await self.client.post("/generate/csv", files={})

        self.assertEqual(response.status_code, 422)

    async def test_oversized_upload_returns_413(self):
        files = self._common_files()
        files["configuration_json"] = (
            "configuration.json",
            b"x" * (MAX_CONFIGURATION_BYTES + 1),
            "application/json",
        )
        files["csv_file"] = (
            "recipients.csv",
            b"recipient_name,certificate_number\nAmina,CERT-001\n",
            "text/csv",
        )

        response = await self.client.post("/generate/csv", files=files)

        self.assertEqual(response.status_code, 413)

    async def test_known_pdf_validation_error_returns_4xx(self):
        files = self._common_files()
        files["certificate_pdf"] = (
            "template.pdf",
            make_pdf(pages=2),
            "application/pdf",
        )
        files["csv_file"] = (
            "recipients.csv",
            b"recipient_name,certificate_number\nAmina,CERT-001\n",
            "text/csv",
        )

        response = await self.client.post("/generate/csv", files=files)

        self.assertEqual(response.status_code, 422)
        self.assertIn("exactly one page", response.json()["detail"])

    async def test_docx_csv_endpoint_success(self):
        files = self._common_docx_files()
        files["csv_file"] = (
            "recipients.csv",
            b"recipient_name,certificate_number\nAmina,CERT-001\n",
            "text/csv",
        )

        response = await self.client.post("/generate/docx/csv", files=files)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._zip_names(response), ["CERT-001.docx"])
        with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
            document = Document(io.BytesIO(archive.read("CERT-001.docx")))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
        self.assertIn("Amina", text)

    async def test_docx_manual_endpoint_success(self):
        files = self._common_docx_files()
        files["recipients_json"] = (
            "recipients.json",
            json.dumps(
                [{"recipient_name": "Naledi", "certificate_number": "CERT-002"}]
            ).encode(),
            "application/json",
        )

        response = await self.client.post("/generate/docx/manual", files=files)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self._zip_names(response), ["CERT-002.docx"])

    async def test_docx_endpoint_rejects_non_docx_filename(self):
        files = self._common_docx_files()
        files["certificate_docx"] = (
            "template.doc",
            make_docx(),
            "application/msword",
        )
        files["csv_file"] = (
            "recipients.csv",
            b"recipient_name,certificate_number\nAmina,CERT-001\n",
            "text/csv",
        )

        response = await self.client.post("/generate/docx/csv", files=files)

        self.assertEqual(response.status_code, 422)
        self.assertIn(".docx", response.json()["detail"])
