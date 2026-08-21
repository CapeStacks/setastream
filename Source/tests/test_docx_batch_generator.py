import io
import unittest
import zipfile

from docx import Document

from certificate_engine.docx_batch_generator import generate_docx_batch_zip

from .helpers import configuration, make_docx


class DocxBatchGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.configuration = configuration()
        self.template = make_docx()

    def _archive(self, raw):
        return zipfile.ZipFile(io.BytesIO(raw))

    def test_generates_rendered_docx_files(self):
        output = generate_docx_batch_zip(
            self.template,
            self.configuration,
            [
                {"recipient_name": "Amina", "certificate_number": "CERT-001"},
                {"recipient_name": "Naledi", "certificate_number": "CERT-002"},
            ],
        )

        with self._archive(output) as archive:
            self.assertEqual(
                archive.namelist(), ["CERT-001.docx", "CERT-002.docx"]
            )
            document = Document(io.BytesIO(archive.read("CERT-001.docx")))
            text = "\n".join(paragraph.text for paragraph in document.paragraphs)
            self.assertIn("Amina", text)

    def test_duplicate_and_unsafe_filenames_are_safe_and_unique(self):
        output = generate_docx_batch_zip(
            self.template,
            self.configuration,
            [
                {
                    "recipient_name": "Amina",
                    "certificate_number": "../../CERT 001.docx",
                },
                {
                    "recipient_name": "Naledi",
                    "certificate_number": "../../CERT 001.docx",
                },
            ],
        )

        with self._archive(output) as archive:
            self.assertEqual(
                archive.namelist(), ["CERT-001.docx", "CERT-001-2.docx"]
            )
