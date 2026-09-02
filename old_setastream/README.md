# Archived SetaStream implementation

This directory preserves the original client-specific certificate workflow.
That workflow managed courses, learners, training-provider data, SAQA and
accreditation details, certificate numbering, DOCX templates, issued
certificates, and audit logs. It no longer matches SetaStream's product
direction, which is a configuration-driven PDF certificate generator.

The legacy Django app, its migrations, management command, domain tests, and
DOCX fixtures retain their former structure under `old_setastream/Source/` so
the implementation and its history remain available for reference.

The archive is not imported by the active application. Authentication, signup,
the existing login templates, Django project files, shared static assets, and
PostgreSQL configuration remain active under `Source/`. The reusable
authentication and signup tests were also retained in `Source/tests/`.

No legacy database tables or migration records were dropped. Restoring this
workflow would require deliberately moving the app back into `Source`, adding
it to `INSTALLED_APPS`, and restoring its legacy-only runtime dependencies.
