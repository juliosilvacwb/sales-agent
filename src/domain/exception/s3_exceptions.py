"""Domain-specific exceptions for S3 storage operations."""


class S3ConnectionError(Exception):
    """Raised when S3 connection fails due to auth errors, missing objects, or network timeouts."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)
