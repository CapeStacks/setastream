import io
import unittest
import zipfile

from pypdf import PdfReader

from certificate_engine.batch_generator import generate_batch_zip
from certificate_engine.config import TemplateConfig
from certificate_engine.exceptions import BatchGenerationError

from .helpers import configuration, configuration_mapping, make_pdf


class BatchGeneratorTests(unittest.TestCase):
    def setUp(self):
        self.configuration = configuration()
        self.template = make_pdf()

    def _names_and_files(self, zip_bytes):
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            return archive.namelist(), {
                name: archive.read(name) for name in archive.namelist()
            }

    def test_one_record_produces_one_pdf_in_zip(self):
        output = generate_batch_zip(
            self.template,
            self.configuration,
            [{"recipient_name": "Amina", "certificate_number": "CERT-001"}],
        )
        names, files = self._names_and_files(output)

        self.assertEqual(names, ["CERT-001.pdf"])
        self.assertEqual(len(PdfReader(io.BytesIO(files[names[0]])).pages), 1)

    def test_two_records_produce_two_pdfs(self):
        output = generate_batch_zip(
            self.template,
            self.configuration,
            [
                {"recipient_name": "Amina", "certificate_number": "CERT-001"},
                {"recipient_name": "Naledi", "certificate_number": "CERT-002"},
            ],
        )
        names, _files = self._names_and_files(output)

        self.assertEqual(names, ["CERT-001.pdf", "CERT-002.pdf"])

    def test_duplicate_filenames_receive_deterministic_suffixes(self):
        output = generate_batch_zip(
            self.template,
            self.configuration,
            [
                {"recipient_name": "A", "certificate_number": "CERT-001"},
                {"recipient_name": "B", "certificate_number": "CERT-001"},
                {"recipient_name": "C", "certificate_number": "CERT-001"},
            ],
        )
        names, _files = self._names_and_files(output)

        self.assertEqual(
            names,
            ["CERT-001.pdf", "CERT-001-2.pdf", "CERT-001-3.pdf"],
        )

    def test_unsafe_filenames_are_sanitized_without_paths(self):
        output = generate_batch_zip(
            self.template,
            self.configuration,
            [
                {
                    "recipient_name": "Amina",
                    "certificate_number": "../../CERT 001\\private",
                }
            ],
        )
        names, _files = self._names_and_files(output)

        self.assertEqual(names, ["CERT-001-private.pdf"])
        self.assertNotIn("/", names[0])
        self.assertNotIn("\\", names[0])

    def test_missing_filename_field_uses_numbered_fallback(self):
        value = configuration_mapping(filename_field="optional_reference")
        fallback_configuration = TemplateConfig.from_mapping(value)

        output = generate_batch_zip(
            self.template,
            fallback_configuration,
            [{"recipient_name": "Amina", "certificate_number": "CERT-001"}],
        )
        names, _files = self._names_and_files(output)

        self.assertEqual(names, ["certificate-1.pdf"])

    def test_a_failing_record_aborts_the_batch(self):
        value = configuration_mapping()
        value["fields"][0].update(
            {"max_width": 0.01, "font_size": 12, "minimum_font_size": 12}
        )
        narrow_configuration = TemplateConfig.from_mapping(value)

        with self.assertRaisesRegex(BatchGenerationError, "Record 1"):
            generate_batch_zip(
                self.template,
                narrow_configuration,
                [
                    {
                        "recipient_name": "This name cannot fit",
                        "certificate_number": "CERT-001",
                    }
                ],
            )
