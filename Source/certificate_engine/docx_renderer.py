"""Placeholder-based rendering for Microsoft Word DOCX templates."""

from __future__ import annotations

import io
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass

from docxtpl import DocxTemplate as DocxTemplateDocument

from .config import TemplateConfig
from .exceptions import DOCXValidationError


MAX_DOCX_BYTES = 10 * 1024 * 1024
REQUIRED_DOCX_PARTS = frozenset({"[Content_Types].xml", "word/document.xml"})


@dataclass(frozen=True, slots=True)
class DocxTemplate:
    data: bytes
    placeholders: frozenset[str]


def load_docx_template(
    raw: bytes, *, maximum_bytes: int = MAX_DOCX_BYTES
) -> DocxTemplate:
    """Validate a DOCX package and return its available placeholders."""

    if not raw:
        raise DOCXValidationError("Certificate DOCX template is empty.")
    if len(raw) > maximum_bytes:
        raise DOCXValidationError(
            f"Certificate DOCX exceeds the {maximum_bytes // (1024 * 1024)} MB limit."
        )

    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if not REQUIRED_DOCX_PARTS.issubset(archive.namelist()):
                raise DOCXValidationError(
                    "Certificate template must be a valid Microsoft Word .docx file."
                )
            if archive.testzip() is not None:
                raise DOCXValidationError("Certificate DOCX template is corrupted.")

        document = DocxTemplateDocument(io.BytesIO(raw))
        placeholders = document.get_undeclared_template_variables()
    except DOCXValidationError:
        raise
    except Exception as exc:
        raise DOCXValidationError("Certificate DOCX template is malformed.") from exc

    return DocxTemplate(data=raw, placeholders=frozenset(placeholders))


def generate_docx_certificate(
    template_docx: DocxTemplate | bytes,
    configuration: TemplateConfig,
    record: Mapping[str, str],
) -> bytes:
    """Replace configured placeholders while preserving the DOCX layout."""

    template = (
        template_docx
        if isinstance(template_docx, DocxTemplate)
        else load_docx_template(template_docx)
    )
    missing_placeholders = sorted(
        set(configuration.required_data_keys) - template.placeholders
    )
    if missing_placeholders:
        raise DOCXValidationError(
            "Certificate DOCX template is missing configured placeholders: "
            + ", ".join(f"{{{{ {name} }}}}" for name in missing_placeholders)
            + "."
        )

    try:
        document = DocxTemplateDocument(io.BytesIO(template.data))
        document.render(dict(record), autoescape=True)
        output = io.BytesIO()
        document.save(output)
    except Exception as exc:
        raise DOCXValidationError("Certificate DOCX template could not be rendered.") from exc
    return output.getvalue()
