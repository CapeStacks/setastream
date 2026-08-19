import unittest

from certificate_engine.csv_parser import parse_csv
from certificate_engine.exceptions import CSVValidationError

from .helpers import configuration


class CsvParserTests(unittest.TestCase):
    def setUp(self):
        self.configuration = configuration()

    def test_valid_csv_with_one_row(self):
        records = parse_csv(
            b"recipient_name,certificate_number\nThando Mokoena,CERT-001\n",
            self.configuration,
        )

        self.assertEqual(
            records,
            [{"recipient_name": "Thando Mokoena", "certificate_number": "CERT-001"}],
        )

    def test_valid_csv_with_multiple_rows(self):
        records = parse_csv(
            b"recipient_name,certificate_number\nAmina,CERT-001\nNaledi,CERT-002\n",
            self.configuration,
        )

        self.assertEqual(len(records), 2)
        self.assertEqual(records[1]["recipient_name"], "Naledi")

    def test_utf8_byte_order_mark(self):
        csv_bytes = (
            "recipient_name,certificate_number\nThandö Mokoena,CERT-001\n"
        ).encode("utf-8-sig")

        records = parse_csv(csv_bytes, self.configuration)

        self.assertEqual(records[0]["recipient_name"], "Thandö Mokoena")

    def test_empty_csv_is_rejected(self):
        with self.assertRaisesRegex(CSVValidationError, "empty"):
            parse_csv(b"", self.configuration)

    def test_completely_blank_rows_are_ignored(self):
        records = parse_csv(
            b"recipient_name,certificate_number\n,\n  ,  \nAmina,CERT-001\n\n",
            self.configuration,
        )

        self.assertEqual(len(records), 1)

    def test_missing_required_columns_are_reported(self):
        with self.assertRaisesRegex(
            CSVValidationError, "certificate_number"
        ):
            parse_csv(b"recipient_name\nAmina\n", self.configuration)

    def test_row_limit_is_enforced_without_truncation(self):
        csv_bytes = (
            b"recipient_name,certificate_number\n"
            b"A,CERT-1\nB,CERT-2\nC,CERT-3\n"
        )

        with self.assertRaisesRegex(CSVValidationError, "maximum of 2"):
            parse_csv(csv_bytes, self.configuration, maximum_records=2)
