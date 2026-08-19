"""Validated configuration objects for PDF template fields."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping

from .exceptions import ConfigurationError


BUILT_IN_FONTS = frozenset(
    {
        "Courier",
        "Courier-Bold",
        "Courier-BoldOblique",
        "Courier-Oblique",
        "Helvetica",
        "Helvetica-Bold",
        "Helvetica-BoldOblique",
        "Helvetica-Oblique",
        "Symbol",
        "Times-Bold",
        "Times-BoldItalic",
        "Times-Italic",
        "Times-Roman",
        "ZapfDingbats",
    }
)
ALIGNMENTS = frozenset({"left", "center", "right"})
HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")


def _required_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{label} must be a non-empty string.")
    return value.strip()


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigurationError(f"{label} must be a number.")
    result = float(value)
    if not math.isfinite(result):
        raise ConfigurationError(f"{label} must be a finite number.")
    return result


def _normalized_number(value: Any, label: str, *, allow_zero: bool = True) -> float:
    result = _number(value, label)
    minimum = 0 if allow_zero else 0.0
    if result < minimum or result > 1 or (not allow_zero and result == 0):
        interval = "greater than 0 and at most 1" if not allow_zero else "from 0 to 1"
        raise ConfigurationError(f"{label} must be {interval}.")
    return result


@dataclass(frozen=True, slots=True)
class FieldConfig:
    """Placement and typography for one dynamic value on a PDF page."""

    name: str
    data_key: str
    x: float
    y: float
    max_width: float
    font_name: str
    font_size: float
    minimum_font_size: float
    alignment: str
    color: str

    @classmethod
    def from_mapping(cls, value: Any, index: int) -> FieldConfig:
        label = f"fields[{index}]"
        if not isinstance(value, Mapping):
            raise ConfigurationError(f"{label} must be a JSON object.")

        font_name = _required_string(value.get("font_name"), f"{label}.font_name")
        if font_name not in BUILT_IN_FONTS:
            raise ConfigurationError(
                f"{label}.font_name must be a ReportLab built-in font; "
                f"received '{font_name}'."
            )

        alignment = _required_string(
            value.get("alignment"), f"{label}.alignment"
        ).lower()
        if alignment == "centre":
            alignment = "center"
        if alignment not in ALIGNMENTS:
            raise ConfigurationError(
                f"{label}.alignment must be left, center, or right."
            )

        color = _required_string(value.get("color"), f"{label}.color")
        if not HEX_COLOR_PATTERN.fullmatch(color):
            raise ConfigurationError(f"{label}.color must use #RRGGBB format.")

        font_size = _number(value.get("font_size"), f"{label}.font_size")
        minimum_font_size = _number(
            value.get("minimum_font_size"), f"{label}.minimum_font_size"
        )
        if font_size <= 0:
            raise ConfigurationError(f"{label}.font_size must be greater than 0.")
        if minimum_font_size <= 0:
            raise ConfigurationError(
                f"{label}.minimum_font_size must be greater than 0."
            )
        if minimum_font_size > font_size:
            raise ConfigurationError(
                f"{label}.minimum_font_size cannot exceed font_size."
            )

        return cls(
            name=_required_string(value.get("name"), f"{label}.name"),
            data_key=_required_string(value.get("data_key"), f"{label}.data_key"),
            x=_normalized_number(value.get("x"), f"{label}.x"),
            y=_normalized_number(value.get("y"), f"{label}.y"),
            max_width=_normalized_number(
                value.get("max_width"), f"{label}.max_width", allow_zero=False
            ),
            font_name=font_name,
            font_size=font_size,
            minimum_font_size=minimum_font_size,
            alignment=alignment,
            color=color.upper(),
        )


@dataclass(frozen=True, slots=True)
class TemplateConfig:
    """A complete, validated internal template configuration."""

    template_name: str
    filename_field: str
    fields: tuple[FieldConfig, ...]

    @classmethod
    def from_mapping(cls, value: Any) -> TemplateConfig:
        if not isinstance(value, Mapping):
            raise ConfigurationError("Configuration JSON must contain an object.")

        raw_fields = value.get("fields")
        if not isinstance(raw_fields, list) or not raw_fields:
            raise ConfigurationError("Configuration fields must be a non-empty array.")

        fields = tuple(
            FieldConfig.from_mapping(field_value, index)
            for index, field_value in enumerate(raw_fields)
        )
        names = [field.name for field in fields]
        duplicate_names = sorted({name for name in names if names.count(name) > 1})
        if duplicate_names:
            raise ConfigurationError(
                "Configuration field names must be unique; duplicates: "
                + ", ".join(duplicate_names)
                + "."
            )

        return cls(
            template_name=_required_string(value.get("template_name"), "template_name"),
            filename_field=_required_string(
                value.get("filename_field"), "filename_field"
            ),
            fields=fields,
        )

    @classmethod
    def from_json_bytes(cls, raw: bytes) -> TemplateConfig:
        if not raw:
            raise ConfigurationError("Configuration JSON file is empty.")
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ConfigurationError(
                "Configuration JSON must use UTF-8 encoding."
            ) from exc
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ConfigurationError(
                f"Configuration JSON is malformed at line {exc.lineno}, "
                f"column {exc.colno}."
            ) from exc
        return cls.from_mapping(value)

    @property
    def required_data_keys(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(field.data_key for field in self.fields))
