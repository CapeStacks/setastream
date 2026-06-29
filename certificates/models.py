from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


def validate_docx_extension(value):
    if not value.name.lower().endswith(".docx"):
        raise ValidationError("Template file must be a .docx file.")


class Course(models.Model):
    name                = models.CharField(max_length=200)
    level               = models.CharField(max_length=50)
    credits             = models.PositiveIntegerField()
    saqa_id             = models.CharField(max_length=20)
    course_code         = models.CharField(max_length = 50, blank=True, help_text="Internal course code shown on the certificate, e.g. 'BLS 1260'")
    accreditation_body  = models.CharField(max_length=200)
    validity_months     = models.PositiveIntegerField(default=36)
    template_file       = models.FileField(
        upload_to       ="course_templates/", validators=[validate_docx_extension]
    )
    is_active           = models.BooleanField(default=True)
    created_at          = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - {self.level}"


class Learner(models.Model):
    ID_TYPE_CHOICES = [
        ("sa_id", "SA ID"),
        ("passport", "Passport"),
    ]

    full_name = models.CharField(max_length=200)
    id_number = models.CharField(max_length=20, unique=True)
    id_type = models.CharField(max_length=20, choices=ID_TYPE_CHOICES, default="sa_id")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.id_number})"


class Certificate(models.Model):
    STATUS_CHOICES = [
        ("issued", "Issued"),
        ("cancelled", "Cancelled"),
        ("reissued", "Reissued"),
    ]

    certificate_number = models.CharField(max_length=20, unique=True)
    learner = models.ForeignKey(Learner, on_delete=models.PROTECT)
    course = models.ForeignKey(Course, on_delete=models.PROTECT)
    learner_name_snapshot = models.CharField(max_length=200)
    course_name_snapshot = models.CharField(max_length=200)
    training_date = models.DateField()
    issue_date = models.DateField()
    expiry_date = models.DateField()
    assessor_name = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="issued")
    issued_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    pdf_file = models.FileField(upload_to="certificates/%Y/%m/", blank=True)
    replaced_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="replaces",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.certificate_number


class CertificateNumberSequence(models.Model):
    last_number = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ("issued", "Issued"),
        ("cancelled", "Cancelled"),
        ("reissued", "Reissued"),
        ("viewed", "Viewed"),
        ("downloaded", "Downloaded"),
    ]

    certificate = models.ForeignKey(
        Certificate, on_delete=models.PROTECT, related_name="audit_logs"
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
