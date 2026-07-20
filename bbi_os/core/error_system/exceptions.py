class BBIOSError(Exception):
    """Base exception for structured BBIOS API error responses."""


class ValidationError(BBIOSError):
    """Raised when input fails application-level validation."""


class NotFoundError(BBIOSError):
    """Raised when a requested resource cannot be found."""


class RepositoryError(BBIOSError):
    """Raised when repository operations fail."""
