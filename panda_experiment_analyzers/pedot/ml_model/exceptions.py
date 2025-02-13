"""Custom exceptions for PEDOT ML model."""


class PEDOTModelError(Exception):
    """Base exception for PEDOT ML model errors."""

    pass


class ModelLoadError(PEDOTModelError):
    """Raised when model loading fails."""

    pass


class ModelSaveError(PEDOTModelError):
    """Raised when model saving fails."""

    pass


class ParameterValidationError(PEDOTModelError):
    """Raised when parameter validation fails."""

    pass
