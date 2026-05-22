from dateutil.relativedelta import relativedelta

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from .models import (
    AuditLog,
    Certificate,
    CertificateNumberSequence,
    Course,
    Learner,
)
from .services import generate_certificate_pdf, generate_next_certificate_number

# Field order shown (read-only) on the change view of an issued certificate.
CERTIFICATE_DETAIL_FIELDS = [
    "certificate_number",
    "status",
    "learner",
    "course",
    "learner_name_snapshot",
    "course_name_snapshot",
    "training_date",
    "issue_date",
    "expiry_date",
    "assessor_name",
    "issued_by",
    "pdf_file",
    "replaced_by",
    "created_at",
]

# Fields the admin fills in on the Add form. Everything else is derived
# automatically in save_model().
CERTIFICATE_ADD_FIELDS = [
    "learner",
    "course",
    "training_date",
    "issue_date",
    "assessor_name",
]


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = [
        "certificate_number",
        "learner_name_snapshot",
        "course_name_snapshot",
        "issue_date",
        "expiry_date",
        "status",
        "issued_by",
    ]
    search_fields = [
        "certificate_number",
        "learner_name_snapshot",
        "learner__id_number",
    ]
    list_filter = ["status", "course", "issue_date"]

    def get_fields(self, request, obj=None):
        if obj is None:
            return CERTIFICATE_ADD_FIELDS
        return CERTIFICATE_DETAIL_FIELDS

    def get_readonly_fields(self, request, obj=None):
        # Existing certificates are immutable: everything is read-only.
        if obj is None:
            return ()
        return [field.name for field in self.model._meta.fields]

    def get_changeform_initial_data(self, request):
        return {"issue_date": timezone.localdate()}

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "course":
            kwargs["queryset"] = Course.objects.filter(is_active=True)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        self.message_user(
            request,
            "Issued certificates cannot be edited. Use the 'Cancel and "
            "reissue' action if changes are needed.",
            level=messages.WARNING,
        )
        return super().change_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        # Editing an existing certificate is forbidden -- they are records.
        if change:
            raise PermissionDenied("Issued certificates cannot be edited.")

        # Cert creation, its audit log, and PDF generation must succeed or fail
        # together. If LibreOffice/rendering fails, the whole issuance (and the
        # certificate-number increment) rolls back.
        with transaction.atomic():
            obj.certificate_number = generate_next_certificate_number()
            obj.learner_name_snapshot = obj.learner.full_name
            obj.course_name_snapshot = obj.course.name
            obj.expiry_date = obj.issue_date + relativedelta(
                months=obj.course.validity_months
            )
            obj.status = "issued"
            obj.issued_by = request.user
            obj.save()

            AuditLog.objects.create(
                certificate=obj,
                action="issued",
                performed_by=request.user,
                reason="Certificate issued via admin (PDF generated)",
                metadata={},
            )

            generate_certificate_pdf(obj)


@admin.register(Learner)
class LearnerAdmin(admin.ModelAdmin):
    list_display = ["full_name", "id_number", "id_type", "email"]
    search_fields = ["full_name", "id_number", "email"]


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "level",
        "credits",
        "saqa_id",
        "accreditation_body",
        "is_active",
    ]
    list_filter = ["is_active", "accreditation_body"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    # Audit logs are written programmatically only -- never via the admin.
    list_display = ["timestamp", "certificate", "action", "performed_by"]
    list_filter = ["action"]
    readonly_fields = [
        "certificate",
        "action",
        "performed_by",
        "reason",
        "metadata",
        "timestamp",
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CertificateNumberSequence)
class CertificateNumberSequenceAdmin(admin.ModelAdmin):
    # The sequence is only ever changed via the set_starting_number command.
    list_display = ["last_number", "updated_at"]
    readonly_fields = ["last_number", "updated_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
