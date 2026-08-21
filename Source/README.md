# SetaStream certificate engine

SetaStream's logic-only engine creates personalized certificates from either
an original one-page PDF template or a Microsoft Word `.docx` template, an
internal field configuration, and recipient data. Recipient data can come
from a UTF-8 CSV file or a JSON array. Every request returns a ZIP containing
one PDF or DOCX file per recipient.

The existing Django project currently owns authentication and the login
screen. The FastAPI application is a development adapter for exercising the
new engine before a final Django UI exists.

## Active directories

- `certificate_engine/` contains framework-independent parsing, validation,
  PDF and DOCX rendering, filename safety, and ZIP batching.
- `fastapi_test_app/` receives multipart uploads and translates known engine
  errors into HTTP responses. It contains no rendering loops or PDF drawing.
- `main/`, `templates/`, and `static/` retain the existing Django login and
  PostgreSQL-backed authentication project.
- `tests/` contains engine, API, authentication, and signup tests. Test PDFs
  are generated programmatically and contain no client documents.
- `../old_setastream/` preserves the retired Course/Learner/DOCX workflow.

## Required inputs

Every generation request requires:

1. Either a valid, unencrypted, one-page `.pdf` template or a valid `.docx`
   template, no larger than 10 MB.
2. A UTF-8 template-configuration JSON file, no larger than 256 KB.
3. Either a UTF-8 CSV file or a manual recipient JSON file, no larger than
   2 MB and containing no more than 500 non-blank records.

The 500-record limit protects this synchronous in-memory test service. Rows
are never silently truncated. CSV content and generated output are not stored
permanently.

## Template configuration

```json
{
  "template_name": "First Aid Certificate",
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
      "color": "#000000"
    }
  ]
}
```

`x`, `y`, and `max_width` are normalized values from 0 to 1. The engine
multiplies them by the original page dimensions. Coordinates use the PDF
bottom-left origin: `x: 0` is the left edge and `y: 0` is the bottom edge.
`x` is the text anchor, interpreted according to `left`, `center`, or `right`
alignment. `max_width` is a fraction of the full page width.

The first version accepts ReportLab's built-in fonts only. Text begins at
`font_size` and shrinks in half-point steps until it fits. Generation fails
clearly if it still exceeds `max_width` at `minimum_font_size`. This font-name
boundary is the extension point for managed custom fonts later.

For DOCX generation, place configured `data_key` values directly in the Word
template using Jinja-style placeholders, for example `{{ recipient_name }}`
and `{{ certificate_number }}`. Word controls the text placement and styling;
the PDF-only coordinates, font, alignment, and color settings are ignored by
the DOCX renderer. Every configured `data_key` must have a matching placeholder
in the DOCX template.

## Recipient formats

CSV headers must contain every configured `data_key`:

```csv
recipient_name,certificate_number,issue_date
Thando Mokoena,CERT-001,18 August 2026
Naledi Dlamini,CERT-002,18 August 2026
```

UTF-8 files with a byte-order mark are supported. Completely blank rows are
ignored; missing columns, missing values, malformed CSV, empty data, and row
limit violations are rejected.

Manual JSON must be a non-empty array:

```json
[
  {
    "recipient_name": "Thando Mokoena",
    "certificate_number": "CERT-001",
    "issue_date": "18 August 2026"
  }
]
```

The configured `filename_field` supplies each PDF filename when present.
Unsafe characters and path separators are sanitized. Missing values fall back
to `certificate-1.pdf`, and duplicates become `CERT-001-2.pdf`,
`CERT-001-3.pdf`, and so on.

## Run the FastAPI test application

From `Source/`:

```bash
../.venv/bin/python -m uvicorn fastapi_test_app.main:app --reload --port 8001
```

Open `http://127.0.0.1:8001/docs`. Use either `POST /generate/csv` or
`POST /generate/manual` to upload all three inputs. Both return
`generated-certificates.zip` containing PDFs. Use `POST /generate/docx/csv`
or `POST /generate/docx/manual` with a `certificate_docx` upload to receive
`generated-word-certificates.zip` containing rendered Word documents.
`GET /health` provides a basic availability check.

Known input and generation errors return HTTP 422, oversized uploads return
HTTP 413, and missing multipart fields use FastAPI's HTTP 422 response.

## Run tests

From the repository root, run the logic and FastAPI tests without a database:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=Source ./.venv/bin/python -m unittest -v \
  tests.test_config tests.test_csv_parser tests.test_pdf_renderer \
  tests.test_batch_generator tests.test_docx_renderer \
  tests.test_docx_batch_generator tests.test_fastapi_api
```

Run the preserved Django authentication tests with a PostgreSQL role that can
create a Django test database:

```bash
cd Source
../.venv/bin/python manage.py test tests.test_authentication tests.test_signup
../.venv/bin/python manage.py check
```

## Failure policy and limitations

Batch generation is fail-fast. If one record cannot be rendered, no partial
ZIP is returned; the error identifies the failing record. This is the simplest
predictable first-version policy.

This phase deliberately has no final UI, visual field editor, automatic field
detection, image templates, custom font uploads, permanent certificate store,
database models for templates or jobs, background workers, email delivery, or
production deployment. Legacy binary `.doc` templates are not supported and
must first be saved as `.docx`. DOCX output is not automatically converted to
PDF. The PDF renderer does not rasterize the original PDF; ReportLab adds
vector text and pypdf merges that overlay over the source page. Built-in fonts
have limited Unicode coverage, and coordinates currently assume a conventional
unrotated PDF page; CapeStacks must verify each managed template configuration.

Django can later import `certificate_engine` directly, call `parse_csv()` or
`parse_manual_records()`, and pass those records to `generate_batch_zip()`.
No FastAPI request object or Django model is required. A future visual editor
only needs to produce the same validated normalized-coordinate configuration;
the renderer does not need to change.
