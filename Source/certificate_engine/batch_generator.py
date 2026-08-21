"""Fail-fast ZIP generation shared by CSV and manual input modes."""

from __future__ import annotations

import io
import re
import unicodedata
import zipfile
from collections.abc import Mapping, Sequence
from typing import Any

from .config import TemplateConfig
from .exceptions import BatchGenerationError, CertificateEngineError
from .pdf_renderer import generate_certificate, load_pdf_template
from .records import normalize_records


MAX_FILENAME_LENGTH = 100


def sanitize_filename_component(value: Any, fallback: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).strip()
    text = text.replace("/", "-").replace("\\", "-")
    text = re.sub(r"[^\w.-]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-+", "-", text).strip(" .-_")
    for extension in (".docx", ".pdf"):
        if text.lower().endswith(extension):
            text = text[: -len(extension)].rstrip(" .-_")
            break
    if not text or text in {".", ".."}:
        text = fallback
    return text[:MAX_FILENAME_LENGTH].rstrip(" .-_") or fallback


def _unique_pdf_filename(base: str, used_names: set[str]) -> str:
    return unique_filename(base, ".pdf", used_names)


def unique_filename(base: str, extension: str, used_names: set[str]) -> str:
    candidate = f"{base}{extension}"
    suffix = 2
    while candidate.casefold() in used_names:
        candidate = f"{base}-{suffix}{extension}"
        suffix += 1
    used_names.add(candidate.casefold())
    return candidate


def generate_batch_zip(
    template_pdf: bytes,
    configuration: TemplateConfig,
    records: Sequence[Mapping[str, Any]],
) -> bytes:
    """Generate every certificate or fail without returning a partial archive."""

    template = load_pdf_template(template_pdf)
    normalized_records = normalize_records(records, configuration)
    used_names: set[str] = set()
    output = io.BytesIO()

    with zipfile.ZipFile(
        output, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as archive:
        for record_number, record in enumerate(normalized_records, start=1):
            fallback = f"certificate-{record_number}"
            filename_value = record.get(configuration.filename_field, "")
            base_name = sanitize_filename_component(filename_value, fallback)
            filename = _unique_pdf_filename(base_name, used_names)
            try:
                certificate_pdf = generate_certificate(
                    template, configuration, record
                )
            except CertificateEngineError as exc:
                raise BatchGenerationError(
                    f"Record {record_number} ({filename}) failed: {exc}"
                ) from exc
            archive.writestr(filename, certificate_pdf)

    return output.getvalue()
