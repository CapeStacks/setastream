"""Business logic for the certificates app.

Kept separate from models and views so it is easy to test and reason about.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.files import File
from django.db import transaction

from docxtpl import DocxTemplate

from .models import CertificateNumberSequence

# LibreOffice is invoked headlessly to render the filled .docx to PDF.
SOFFICE_BINARY = "/usr/bin/soffice"
SOFFICE_TIMEOUT_SECONDS = 60

# The sequence is a singleton: we always read/write the same row.
SEQUENCE_ID = 1

# Minimum width of the formatted certificate number. f"{n:07d}" pads with
# leading zeros up to 7 chars, but produces MORE digits once n exceeds
# 9,999,999 (e.g. 10000000). Padding is a minimum, not a maximum.
NUMBER_PADDING = 7


@transaction.atomic
def generate_next_certificate_number():
    """Atomically allocate and return the next certificate number.

    Correctness depends on the row-level lock taken by select_for_update():
    without it, two concurrent callers can read the same last_number and
    produce duplicate certificate numbers. Do not "simplify" this away.

    Safe to call from inside a larger atomic block: the @transaction.atomic
    decorator opens a savepoint when already in a transaction, and the lock is
    held until the outermost transaction commits.
    """
    # get_or_create ensures the singleton row exists, but it does NOT take a
    # lock. We must re-fetch the row with select_for_update() to acquire the
    # row-level lock before the read-modify-write below.
    CertificateNumberSequence.objects.get_or_create(
        id=SEQUENCE_ID, defaults={"last_number": 0}
    )
    sequence = CertificateNumberSequence.objects.select_for_update().get(id=SEQUENCE_ID)

    sequence.last_number += 1
    sequence.save()

    return f"{sequence.last_number:0{NUMBER_PADDING}d}"


def render_certificate_docx(certificate) -> Path:
    """Fill the course's .docx template with this certificate's data.

    Returns the path to the rendered .docx, written into a fresh temp
    directory. The caller is responsible for removing that directory
    (generate_certificate_pdf does so).
    """
    context = {
        "learner_name": certificate.learner_name_snapshot,
        "id_number": certificate.learner.id_number,
        "course_name": certificate.course_name_snapshot,
        "certificate_number": certificate.certificate_number,
        "issue_date": certificate.issue_date.strftime("%d %B %Y"),
        "expiry_date": certificate.expiry_date.strftime("%d %B %Y"),
        "assessor_name": certificate.assessor_name or "",
    }

    template = DocxTemplate(certificate.course.template_file.path)
    template.render(context)

    output_dir = Path(tempfile.mkdtemp(prefix="cert_"))
    docx_path = output_dir / f"{certificate.certificate_number}.docx"
    template.save(str(docx_path))
    return docx_path


def convert_docx_to_pdf(docx_path: Path) -> Path:
    """Convert a .docx to PDF using headless LibreOffice.

    LibreOffice replaces the extension with .pdf and writes the result into
    --outdir, so the output name is derived from the input name. Returns the
    path to the produced PDF. Raises CalledProcessError on failure (check=True)
    and TimeoutExpired if LibreOffice hangs past the timeout.
    """
    output_dir = docx_path.parent
    subprocess.run(
        [
            SOFFICE_BINARY,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(docx_path),
        ],
        check=True,
        timeout=SOFFICE_TIMEOUT_SECONDS,
        capture_output=True,
    )
    return output_dir / f"{docx_path.stem}.pdf"


def generate_certificate_pdf(certificate) -> None:
    """Render the template, convert to PDF, and attach it to the certificate.

    Both intermediate files (the filled .docx and the PDF) live in one temp
    directory which is always removed afterwards -- only the final PDF is
    persisted, via the FileField's .save(). Cleanup runs even if conversion
    fails. (A single tempfile.TemporaryDirectory context manager can't span the
    two helpers given their required signatures, so we mkdtemp + rmtree to get
    the same guaranteed cleanup.)
    """
    docx_path = render_certificate_docx(certificate)
    temp_dir = docx_path.parent
    try:
        pdf_path = convert_docx_to_pdf(docx_path)
        with open(pdf_path, "rb") as pdf_fh:
            certificate.pdf_file.save(
                f"{certificate.certificate_number}.pdf",
                File(pdf_fh),
                save=True,
            )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
