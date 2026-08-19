"""UTF-8 CSV parsing for certificate recipient batches."""

from __future__ import annotations

import csv
import io

from .config import TemplateConfig
from .exceptions import CSVValidationError, InputValidationError
from .records import MAX_RECORDS, Record, normalize_records


def parse_csv(
    raw: bytes,
    configuration: TemplateConfig,
    *,
    maximum_records: int = MAX_RECORDS,
) -> list[Record]:
    if not raw:
        raise CSVValidationError("CSV file is empty.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CSVValidationError("CSV file must use UTF-8 encoding.") from exc

    try:
        reader = csv.DictReader(io.StringIO(text, newline=""))
        if reader.fieldnames is None:
            raise CSVValidationError("CSV file must contain a header row.")

        headers = [
            header.strip() if header is not None else ""
            for header in reader.fieldnames
        ]
        if any(not header for header in headers):
            raise CSVValidationError("CSV header contains an empty column name.")
        duplicate_headers = sorted(
            {header for header in headers if headers.count(header) > 1}
        )
        if duplicate_headers:
            raise CSVValidationError(
                "CSV header contains duplicate columns: "
                + ", ".join(duplicate_headers)
                + "."
            )
        reader.fieldnames = headers

        missing_columns = [
            key for key in configuration.required_data_keys if key not in headers
        ]
        if missing_columns:
            raise CSVValidationError(
                "CSV is missing required columns: "
                + ", ".join(missing_columns)
                + "."
            )

        rows: list[dict[str, str | None]] = []
        for row in reader:
            if None in row:
                raise CSVValidationError(
                    f"CSV row {reader.line_num} has more values than the header."
                )
            if not any((value or "").strip() for value in row.values()):
                continue
            rows.append(row)
            if len(rows) > maximum_records:
                raise CSVValidationError(
                    f"CSV exceeds the maximum of {maximum_records} recipient rows."
                )
    except csv.Error as exc:
        raise CSVValidationError(f"CSV file is malformed: {exc}.") from exc

    if not rows:
        raise CSVValidationError("CSV file contains no recipient records.")
    try:
        return normalize_records(
            rows, configuration, maximum_records=maximum_records
        )
    except InputValidationError as exc:
        raise CSVValidationError(str(exc)) from exc
