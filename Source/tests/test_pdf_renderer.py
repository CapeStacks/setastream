import io
import unittest

from pypdf import PdfReader, PdfWriter
from reportlab.pdfbase import pdfmetrics

from certificate_engine.exceptions import PDFValidationError, TextFitError
from certificate_engine.pdf_renderer import (
    calculate_text_x,
    fit_font_size,
    generate_certificate,
    load_pdf_template,
)

from .helpers import configuration, make_pdf


class PdfRendererTests(unittest.TestCase):
    def setUp(self):
        self.configuration = configuration()
        self.record = {
            "recipient_name": "Thando Mokoena",
            "certificate_number": "CERT-001",
        }

    def test_generated_certificate_is_one_page_with_vector_text(self):
        generated = generate_certificate(
            make_pdf(), self.configuration, self.record
        )
        reader = PdfReader(io.BytesIO(generated))

        self.assertEqual(len(reader.pages), 1)
        self.assertIn("Thando Mokoena", reader.pages[0].extract_text())

    def test_original_page_dimensions_are_preserved(self):
        generated = generate_certificate(
            make_pdf(width=500, height=300), self.configuration, self.record
        )
        page = PdfReader(io.BytesIO(generated)).pages[0]

        self.assertEqual(float(page.mediabox.width), 500)
        self.assertEqual(float(page.mediabox.height), 300)

    def test_left_center_and_right_alignment_calculations(self):
        self.assertEqual(calculate_text_x(100, 40, "left"), 100)
        self.assertEqual(calculate_text_x(100, 40, "center"), 80)
        self.assertEqual(calculate_text_x(100, 40, "right"), 60)

    def test_long_text_shrinks_to_fit(self):
        text = "A reasonably long recipient name"
        maximum_width = pdfmetrics.stringWidth(text, "Helvetica", 18)

        fitted = fit_font_size(text, "Helvetica", 32, 10, maximum_width)

        self.assertLess(fitted, 32)
        self.assertGreaterEqual(fitted, 10)
        self.assertLessEqual(
            pdfmetrics.stringWidth(text, "Helvetica", fitted), maximum_width
        )

    def test_text_that_cannot_fit_raises_clear_error(self):
        with self.assertRaisesRegex(TextFitError, "minimum font size"):
            fit_font_size("W" * 100, "Helvetica", 12, 9, 10)

    def test_minimum_size_is_checked_when_not_on_half_point_boundary(self):
        text = "Minimum size"
        minimum_width = pdfmetrics.stringWidth(text, "Helvetica", 9)

        fitted = fit_font_size(text, "Helvetica", 9.2, 9, minimum_width)

        self.assertEqual(fitted, 9)

    def test_invalid_pdf_is_rejected(self):
        with self.assertRaisesRegex(PDFValidationError, "malformed"):
            load_pdf_template(b"not a PDF")

    def test_multi_page_pdf_is_rejected(self):
        with self.assertRaisesRegex(PDFValidationError, "exactly one page"):
            load_pdf_template(make_pdf(pages=2))

    def test_encrypted_pdf_is_rejected(self):
        reader = PdfReader(io.BytesIO(make_pdf()))
        writer = PdfWriter()
        writer.add_page(reader.pages[0])
        writer.encrypt("secret")
        encrypted = io.BytesIO()
        writer.write(encrypted)

        with self.assertRaisesRegex(PDFValidationError, "Encrypted"):
            load_pdf_template(encrypted.getvalue())
