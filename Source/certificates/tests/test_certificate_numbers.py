import threading

from django.core.management import call_command
from django.db import connection
from django.test import TestCase, TransactionTestCase

from Source.certificates.models import CertificateNumberSequence
from Source.certificates.services import generate_next_certificate_number


class CertificateNumberTests(TestCase):
    def test_first_number_is_one(self):
        self.assertEqual(generate_next_certificate_number(), "0000001")

    def test_sequential_increment(self):
        results = [generate_next_certificate_number() for _ in range(5)]
        self.assertEqual(
            results,
            ["0000001", "0000002", "0000003", "0000004", "0000005"],
        )

    def test_padding_format(self):
        number = generate_next_certificate_number()
        self.assertEqual(len(number), 7)
        self.assertEqual(number, "0000001")
        # Zero-padded: parsing back and reformatting is stable.
        self.assertTrue(number.isdigit())

    def test_starting_number_command(self):
        call_command("set_starting_number", 9843215504)

        sequence = CertificateNumberSequence.objects.get(id=1)
        self.assertEqual(sequence.last_number, 9843215504)

        # Padding is a *minimum* of 7 digits, not a maximum: numbers above
        # 9,999,999 are longer than 7 chars.
        next_number = generate_next_certificate_number()
        self.assertEqual(next_number, "9843215505")
        self.assertEqual(len(next_number), 10)


class ConcurrentGenerationTests(TransactionTestCase):
    """Proves the select_for_update() lock prevents duplicate numbers.

    Uses TransactionTestCase (not TestCase) because each thread runs in its own
    DB connection/transaction; TestCase's single wrapping transaction would not
    be visible to the worker threads.
    """

    def test_concurrent_generation(self):
        thread_count = 10
        results = []
        results_lock = threading.Lock()
        # Release all threads at once to maximise contention on the lock.
        barrier = threading.Barrier(thread_count)

        def worker():
            # Connections are thread-local; close any inherited connection so
            # this thread gets its own.
            connection.close()
            try:
                barrier.wait()
                number = generate_next_certificate_number()
                with results_lock:
                    results.append(number)
            finally:
                connection.close()

        threads = [threading.Thread(target=worker) for _ in range(thread_count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(len(results), thread_count)
        # (a) every result is unique
        self.assertEqual(len(set(results)), thread_count)
        # (b) the results are exactly 0000001..0000010 with no gaps
        expected = {f"{i:07d}" for i in range(1, thread_count + 1)}
        self.assertEqual(set(results), expected)
