"""Fail-fast ZIP generation for rendered Microsoft Word certificates."""

from __future__ import annotations

import io
import zipfile
from collections.abc import Mapping, Sequence
from typing import Any

from .batch_generator import sanitize_filename_component, unique_filename
from .config import TemplateConfig
from .docx_renderer import generate_docx_certificate, load_docx_template
from .exceptions import BatchGenerationError, CertificateEngineError
from .records import normalize_records


def generate_docx_batch_zip(
    template_docx: bytes,
    configuration: TemplateConfig,
    records: Sequence[Mapping[str, Any]],
) -> bytes:
    """Generate one rendered DOCX per record or fail without a partial archive."""

    template = load_docx_template(template_docx)
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
            filename = unique_filename(base_name, ".docx", used_names)
            try:
                certificate_docx = generate_docx_certificate(
                    template, configuration, record
                )
            except CertificateEngineError as exc:
                raise BatchGenerationError(
                    f"Record {record_number} ({filename}) failed: {exc}"
                ) from exc
            archive.writestr(filename, certificate_docx)

    return output.getvalue()
