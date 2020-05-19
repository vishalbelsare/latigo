"""Exceptions for the Metadata API logic."""


class MetadataStoringError(Exception):
    """Raise if got not 200 status code from the API."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)
