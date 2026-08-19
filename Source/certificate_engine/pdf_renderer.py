"""Vector text rendering and one-page PDF template merging."""

from __future__ import annotations

import io
from collections.abc import Mapping
from dataclasses import dataclass

from pypdf import PdfReader, PdfWriter
from pypdf.errors import PyPdfError
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfgen import canvas

from .config import TemplateConfig
from .exceptions import PDFValidationError, TextFitError


MAX_PDF_BYTES = 10 * 1024 * 1024
FONT_SIZE_STEP = 0.5


@dataclass(frozen=True, slots=True)
class PdfTemplate:
    data: bytes
    width: float
    height: float


def load_pdf_template(
    raw: bytes, *, maximum_bytes: int = MAX_PDF_BYTES
) -> PdfTemplate:
    if not raw:
        raise PDFValidationError("Certificate PDF template is empty.")
    if len(raw) > maximum_bytes:
        raise PDFValidationError(
            f"Certificate PDF exceeds the {maximum_bytes // (1024 * 1024)} MB limit."
        )
    try:
        reader = PdfReader(io.BytesIO(raw), strict=True)
        if reader.is_encrypted:
            raise PDFValidationError(
                "Encrypted or password-protected PDF templates are not supported."
            )
        if len(reader.pages) != 1:
            raise PDFValidationError(
                "Certificate PDF template must contain exactly one page."
            )
        page = reader.pages[0]
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
    except PDFValidationError:
        raise
    except (PyPdfError, ValueError, TypeError, OSError) as exc:
        raise PDFValidationError("Certificate PDF template is malformed.") from exc
    if width <= 0 or height <= 0:
        raise PDFValidationError("Certificate PDF page dimensions must be positive.")
    return PdfTemplate(data=raw, width=width, height=height)


def fit_font_size(
    text: str,
    font_name: str,
    font_size: float,
    minimum_font_size: float,
    maximum_width: float,
) -> float:
    """Return the largest half-point font size that fits the allowed width."""

    candidate = float(font_size)
    minimum = float(minimum_font_size)
    while candidate > minimum:
        if pdfmetrics.stringWidth(text, font_name, candidate) <= maximum_width:
            return candidate
        candidate = max(minimum, round(candidate - FONT_SIZE_STEP, 2))
    if pdfmetrics.stringWidth(text, font_name, minimum) <= maximum_width:
        return minimum
    raise TextFitError(
        f"Text cannot fit within {maximum_width:.2f} PDF points at the minimum "
        f"font size of {minimum:g}."
    )


def calculate_text_x(anchor_x: float, text_width: float, alignment: str) -> float:
    if alignment == "left":
        return anchor_x
    if alignment == "center":
        return anchor_x - (text_width / 2)
    if alignment == "right":
        return anchor_x - text_width
    raise ValueError(f"Unsupported alignment: {alignment}")


def _build_overlay(
    template: PdfTemplate,
    configuration: TemplateConfig,
    record: Mapping[str, str],
) -> bytes:
    overlay_buffer = io.BytesIO()
    overlay = canvas.Canvas(
        overlay_buffer,
        pagesize=(template.width, template.height),
        pageCompression=1,
    )

    for field in configuration.fields:
        text = record.get(field.data_key, "")
        maximum_width = field.max_width * template.width
        try:
            fitted_size = fit_font_size(
                text,
                field.font_name,
                field.font_size,
                field.minimum_font_size,
                maximum_width,
            )
        except TextFitError as exc:
            raise TextFitError(
                f"Field '{field.name}' value cannot fit at its minimum font size."
            ) from exc

        text_width = pdfmetrics.stringWidth(text, field.font_name, fitted_size)
        anchor_x = field.x * template.width
        draw_x = calculate_text_x(anchor_x, text_width, field.alignment)
        draw_y = field.y * template.height
        overlay.setFillColor(HexColor(field.color))
        overlay.setFont(field.font_name, fitted_size)
        overlay.drawString(draw_x, draw_y, text)

    overlay.showPage()
    overlay.save()
    return overlay_buffer.getvalue()


def generate_certificate(
    template_pdf: PdfTemplate | bytes,
    configuration: TemplateConfig,
    record: Mapping[str, str],
) -> bytes:
    """Merge a vector text overlay over the original one-page PDF."""

    template = (
        template_pdf
        if isinstance(template_pdf, PdfTemplate)
        else load_pdf_template(template_pdf)
    )
    overlay_bytes = _build_overlay(template, configuration, record)

    overlay_reader = PdfReader(io.BytesIO(overlay_bytes), strict=True)
    writer = PdfWriter(clone_from=io.BytesIO(template.data))
    page = writer.pages[0]
    page.merge_page(overlay_reader.pages[0])

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
