"""Development-only HTTP adapter around the reusable certificate engine."""

from __future__ import annotations

from typing import Annotated

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, Response

from certificate_engine import (
    CertificateEngineError,
    TemplateConfig,
    generate_batch_zip,
    generate_docx_batch_zip,
    parse_csv,
    parse_manual_records,
)
from certificate_engine.docx_renderer import MAX_DOCX_BYTES
from certificate_engine.exceptions import InputValidationError
from certificate_engine.pdf_renderer import MAX_PDF_BYTES


MAX_CONFIGURATION_BYTES = 256 * 1024
MAX_RECIPIENT_DATA_BYTES = 2 * 1024 * 1024
DOWNLOAD_FILENAME = "generated-certificates.zip"
DOCX_DOWNLOAD_FILENAME = "generated-word-certificates.zip"


class UploadTooLargeError(CertificateEngineError):
    """An uploaded request part exceeds the test API's in-memory limit."""


app = FastAPI(
    title="SetaStream certificate engine test API",
    description="Generate certificate ZIP files from configured PDF or DOCX templates.",
    version="0.1.0",
)


@app.exception_handler(UploadTooLargeError)
async def handle_upload_too_large(
    _request, exc: UploadTooLargeError
) -> JSONResponse:
    return JSONResponse(status_code=413, content={"detail": str(exc)})


@app.exception_handler(CertificateEngineError)
async def handle_engine_error(
    _request, exc: CertificateEngineError
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


async def _read_upload(upload: UploadFile, label: str, maximum_bytes: int) -> bytes:
    data = await upload.read(maximum_bytes + 1)
    if len(data) > maximum_bytes:
        limit_mb = maximum_bytes / (1024 * 1024)
        display_limit = (
            f"{limit_mb:g} MB"
            if limit_mb >= 1
            else f"{maximum_bytes // 1024} KB"
        )
        raise UploadTooLargeError(f"{label} exceeds the {display_limit} limit.")
    return data


async def _read_common_inputs(
    certificate_pdf: UploadFile,
    configuration_json: UploadFile,
) -> tuple[bytes, TemplateConfig]:
    filename = certificate_pdf.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise InputValidationError("certificate_pdf must be uploaded as a .pdf file.")
    pdf_bytes = await _read_upload(
        certificate_pdf, "Certificate PDF", MAX_PDF_BYTES
    )
    configuration_bytes = await _read_upload(
        configuration_json, "Configuration JSON", MAX_CONFIGURATION_BYTES
    )
    return pdf_bytes, TemplateConfig.from_json_bytes(configuration_bytes)


async def _read_common_docx_inputs(
    certificate_docx: UploadFile,
    configuration_json: UploadFile,
) -> tuple[bytes, TemplateConfig]:
    filename = certificate_docx.filename or ""
    if not filename.lower().endswith(".docx"):
        raise InputValidationError(
            "certificate_docx must be uploaded as a .docx file."
        )
    docx_bytes = await _read_upload(
        certificate_docx, "Certificate DOCX", MAX_DOCX_BYTES
    )
    configuration_bytes = await _read_upload(
        configuration_json, "Configuration JSON", MAX_CONFIGURATION_BYTES
    )
    return docx_bytes, TemplateConfig.from_json_bytes(configuration_bytes)


def _zip_response(
    zip_bytes: bytes, *, filename: str = DOWNLOAD_FILENAME
) -> Response:
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "setastream-certificate-engine"}


@app.post("/generate/csv", response_class=Response)
async def generate_from_csv(
    certificate_pdf: Annotated[
        UploadFile, File(description="One-page certificate PDF template")
    ],
    configuration_json: Annotated[
        UploadFile, File(description="Internal template configuration JSON")
    ],
    csv_file: Annotated[
        UploadFile, File(description="UTF-8 recipient CSV file")
    ],
) -> Response:
    pdf_bytes, configuration = await _read_common_inputs(
        certificate_pdf, configuration_json
    )
    csv_bytes = await _read_upload(
        csv_file, "Recipient CSV", MAX_RECIPIENT_DATA_BYTES
    )
    records = parse_csv(csv_bytes, configuration)
    return _zip_response(generate_batch_zip(pdf_bytes, configuration, records))


@app.post("/generate/manual", response_class=Response)
async def generate_from_manual_records(
    certificate_pdf: Annotated[
        UploadFile, File(description="One-page certificate PDF template")
    ],
    configuration_json: Annotated[
        UploadFile, File(description="Internal template configuration JSON")
    ],
    recipients_json: Annotated[
        UploadFile, File(description="JSON array of recipient records")
    ],
) -> Response:
    pdf_bytes, configuration = await _read_common_inputs(
        certificate_pdf, configuration_json
    )
    recipients_bytes = await _read_upload(
        recipients_json, "Manual recipient JSON", MAX_RECIPIENT_DATA_BYTES
    )
    records = parse_manual_records(recipients_bytes, configuration)
    return _zip_response(generate_batch_zip(pdf_bytes, configuration, records))


@app.post("/generate/docx/csv", response_class=Response)
async def generate_docx_from_csv(
    certificate_docx: Annotated[
        UploadFile, File(description="Word .docx certificate template")
    ],
    configuration_json: Annotated[
        UploadFile, File(description="Internal template configuration JSON")
    ],
    csv_file: Annotated[
        UploadFile, File(description="UTF-8 recipient CSV file")
    ],
) -> Response:
    docx_bytes, configuration = await _read_common_docx_inputs(
        certificate_docx, configuration_json
    )
    csv_bytes = await _read_upload(
        csv_file, "Recipient CSV", MAX_RECIPIENT_DATA_BYTES
    )
    records = parse_csv(csv_bytes, configuration)
    return _zip_response(
        generate_docx_batch_zip(docx_bytes, configuration, records),
        filename=DOCX_DOWNLOAD_FILENAME,
    )


@app.post("/generate/docx/manual", response_class=Response)
async def generate_docx_from_manual_records(
    certificate_docx: Annotated[
        UploadFile, File(description="Word .docx certificate template")
    ],
    configuration_json: Annotated[
        UploadFile, File(description="Internal template configuration JSON")
    ],
    recipients_json: Annotated[
        UploadFile, File(description="JSON array of recipient records")
    ],
) -> Response:
    docx_bytes, configuration = await _read_common_docx_inputs(
        certificate_docx, configuration_json
    )
    recipients_bytes = await _read_upload(
        recipients_json, "Manual recipient JSON", MAX_RECIPIENT_DATA_BYTES
    )
    records = parse_manual_records(recipients_bytes, configuration)
    return _zip_response(
        generate_docx_batch_zip(docx_bytes, configuration, records),
        filename=DOCX_DOWNLOAD_FILENAME,
    )
