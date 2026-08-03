import shutil
import tempfile
from datetime import date
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from docx import Document

from certificates.models import AuditLog, Certificate, Course, Learner

User = get_user_model()


def _docx_bytes(text):
    buffer = BytesIO()
    document = Document()
    document.add_paragraph(text)
    document.save(buffer)
    return buffer.getvalue()


class CertificateAdminIssuanceTests(TestCase):
    def setUp(self):
        # Issuing now generates a PDF, so the course needs a real .docx
        # template and an isolated MEDIA_ROOT to write into.
        self.media_root = tempfile.mkdtemp(prefix="media_")
        override = override_settings(MEDIA_ROOT=self.media_root)
        override.enable()
        self.addCleanup(override.disable)
        self.addCleanup(shutil.rmtree, self.media_root, True)

        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="pass12345",
        )
        self.client.force_login(self.admin)

        self.learner = Learner.objects.create(
            full_name="Thabo Mokoena",
            id_number="9001015800087",
            id_type="sa_id",
        )
        self.course = Course.objects.create(
            name="First Aid Level 1",
            level="Level 1",
            credits=5,
            saqa_id="119567",
            accreditation_body="HWSETA",
            validity_months=36,
            is_active=True,
            template_file=ContentFile(
                _docx_bytes("Certificate {{ learner_name }}"),
                name="template.docx",
            ),
        )

    def _add_url(self):
        return reverse("admin:certificates_certificate_add")

    def _post_data(self, **overrides):
        data = {
            "learner": self.learner.pk,
            "course": self.course.pk,
            "training_date": "2025-01-10",
            "issue_date": "2025-01-15",
            "assessor_name": "Jane Assessor",
        }
        data.update(overrides)
        return data

    def test_create_certificate_via_admin_generates_number(self):
        response = self.client.post(self._add_url(), self._post_data())

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Certificate.objects.count(), 1)
        cert = Certificate.objects.get()
        self.assertEqual(cert.certificate_number, "0000001")

    def test_create_certificate_snapshots_learner_and_course(self):
        self.client.post(self._add_url(), self._post_data())

        cert = Certificate.objects.get()
        self.assertEqual(cert.learner_name_snapshot, "Thabo Mokoena")
        self.assertEqual(cert.course_name_snapshot, "First Aid Level 1")

    def test_create_certificate_computes_expiry(self):
        self.client.post(self._add_url(), self._post_data(issue_date="2025-01-15"))

        cert = Certificate.objects.get()
        # issue_date 2025-01-15 + 36 months -> 2028-01-15
        self.assertEqual(cert.expiry_date, date(2028, 1, 15))

    def test_create_certificate_creates_audit_log(self):
        self.client.post(self._add_url(), self._post_data())

        cert = Certificate.objects.get()
        self.assertEqual(AuditLog.objects.count(), 1)
        log = AuditLog.objects.get()
        self.assertEqual(log.certificate_id, cert.pk)
        self.assertEqual(log.action, "issued")
        self.assertEqual(log.performed_by_id, self.admin.pk)

    def test_cannot_edit_issued_certificate(self):
        self.client.post(self._add_url(), self._post_data())
        cert = Certificate.objects.get()
        original_assessor = cert.assessor_name

        change_url = reverse(
            "admin:certificates_certificate_change", args=[cert.pk]
        )
        response = self.client.post(
            change_url, self._post_data(assessor_name="Hacker McEdit")
        )

        # save_model raises PermissionDenied for edits -> 403, and nothing
        # about the stored certificate changes.
        self.assertEqual(response.status_code, 403)
        cert.refresh_from_db()
        self.assertEqual(cert.assessor_name, original_assessor)

    def test_cannot_delete_issued_certificate(self):
        self.client.post(self._add_url(), self._post_data())
        cert = Certificate.objects.get()

        delete_url = reverse(
            "admin:certificates_certificate_delete", args=[cert.pk]
        )
        response = self.client.post(delete_url, {"post": "yes"})

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Certificate.objects.filter(pk=cert.pk).exists())
