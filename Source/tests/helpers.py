"""Small public-data fixtures shared by the active test suite."""

from __future__ import annotations

import io
import json
from typing import Any

from reportlab.pdfgen import canvas

from certificate_engine.config import TemplateConfig


def make_pdf(*, width: float = 612, height: float = 792, pages: int = 1) -> bytes:
    output = io.BytesIO()
    document = canvas.Canvas(output, pagesize=(width, height))
    for page_number in range(1, pages + 1):
        document.setFont("Helvetica", 10)
        document.drawString(20, height - 30, f"Template background {page_number}")
        document.showPage()
    document.save()
    return output.getvalue()


def configuration_mapping(**overrides: Any) -> dict[str, Any]:
    value: dict[str, Any] = {
        "template_name": "Test Certificate",
        "filename_field": "certificate_number",
        "fields": [
            {
                "name": "recipient_name",
                "data_key": "recipient_name",
                "x": 0.5,
                "y": 0.48,
                "max_width": 0.65,
                "font_name": "Helvetica-Bold",
                "font_size": 32,
                "minimum_font_size": 18,
                "alignment": "center",
                "color": "#000000",
            },
            {
                "name": "certificate_number",
                "data_key": "certificate_number",
                "x": 0.8,
                "y": 0.12,
                "max_width": 0.15,
                "font_name": "Helvetica",
                "font_size": 12,
                "minimum_font_size": 9,
                "alignment": "left",
                "color": "#000000",
            },
        ],
    }
    value.update(overrides)
    return value


def configuration() -> TemplateConfig:
    return TemplateConfig.from_mapping(configuration_mapping())


def configuration_bytes(**overrides: Any) -> bytes:
    return json.dumps(configuration_mapping(**overrides)).encode("utf-8")
