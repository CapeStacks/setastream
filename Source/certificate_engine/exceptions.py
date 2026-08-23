"""Explicit errors raised for expected certificate-generation failures."""


class CertificateEngineError(Exception):
    """Base class for input and generation errors safe to show to a caller."""


class ConfigurationError(CertificateEngineError):
    """The template configuration is missing or invalid."""


class InputValidationError(CertificateEngineError):
    """Recipient input cannot be normalized into usable records."""


class CSVValidationError(InputValidationError):
    """CSV content or structure is invalid."""


class PDFValidationError(CertificateEngineError):
    """The certificate template is not a supported one-page PDF."""


class TextFitError(CertificateEngineError):
    """A configured value cannot fit inside its allowed field width."""


class BatchGenerationError(CertificateEngineError):
    """A record failed while a fail-fast ZIP batch was being generated."""
