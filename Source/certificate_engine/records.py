"""Shared normalization for CSV and manually supplied recipient records."""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from typing import Any

from .config import TemplateConfig
from .exceptions import InputValidationError


MAX_RECORDS = 500
Record = dict[str, str]


def _normalize_value(value: Any, key: str, record_number: int) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        raise InputValidationError(
            f"Record {record_number} field '{key}' must contain a scalar value."
        )
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def normalize_records(
    records: Iterable[Mapping[str, Any]],
    configuration: TemplateConfig,
    *,
    maximum_records: int = MAX_RECORDS,
) -> list[Record]:
    """Normalize different input modes into dictionaries of display strings."""

    normalized: list[Record] = []
    for record_number, raw_record in enumerate(records, start=1):
        if record_number > maximum_records:
            raise InputValidationError(
                f"A maximum of {maximum_records} recipient records is allowed."
            )
        if not isinstance(raw_record, Mapping):
            raise InputValidationError(f"Record {record_number} must be an object.")

        record: Record = {}
        for key, value in raw_record.items():
            if not isinstance(key, str) or not key.strip():
                raise InputValidationError(
                    f"Record {record_number} contains an invalid field name."
                )
            normalized_key = key.strip()
            record[normalized_key] = _normalize_value(
                value, normalized_key, record_number
            )

        for required_key in configuration.required_data_keys:
            if not record.get(required_key):
                raise InputValidationError(
                    f"Record {record_number} is missing a value for required field "
                    f"'{required_key}'."
                )
        normalized.append(record)

    if not normalized:
        raise InputValidationError("At least one recipient record is required.")
    return normalized


def parse_manual_records(
    raw: bytes,
    configuration: TemplateConfig,
    *,
    maximum_records: int = MAX_RECORDS,
) -> list[Record]:
    if not raw:
        raise InputValidationError("Manual recipient JSON file is empty.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise InputValidationError("Manual recipient JSON must use UTF-8 encoding.") from exc
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise InputValidationError(
            f"Manual recipient JSON is malformed at line {exc.lineno}, "
            f"column {exc.colno}."
        ) from exc
    if not isinstance(value, list):
        raise InputValidationError("Manual recipient JSON must contain an array.")
    return normalize_records(value, configuration, maximum_records=maximum_records)
