"""Set the starting certificate number from the command line.

    python manage.py set_starting_number 9843215504

After running this, the next certificate generated will be 9843215505.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from Source.certificates.models import CertificateNumberSequence
from Source.certificates.services import SEQUENCE_ID


class Command(BaseCommand):
    help = "Set the starting certificate number (last_number) for the sequence."

    def add_arguments(self, parser):
        parser.add_argument(
            "number",
            type=int,
            help="Number to set as last_number (non-negative integer).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        number = options["number"]
        if number < 0:
            raise CommandError("Number must be a non-negative integer.")

        # Same locking pattern as the generation service: ensure the singleton
        # row exists, then take the row-level lock with select_for_update().
        CertificateNumberSequence.objects.get_or_create(
            id=SEQUENCE_ID, defaults={"last_number": 0}
        )
        sequence = CertificateNumberSequence.objects.select_for_update().get(
            id=SEQUENCE_ID
        )

        if sequence.last_number > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"A sequence already exists with last_number="
                    f"{sequence.last_number}."
                )
            )
            answer = input(
                f"Overwrite and set last_number to {number}? [y/N]: "
            )
            if answer.strip().lower() not in ("y", "yes"):
                raise CommandError("Aborted. Sequence was not changed.")

        sequence.last_number = number
        sequence.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Starting number set to {number}. "
                f"Next certificate will be {number + 1}."
            )
        )
