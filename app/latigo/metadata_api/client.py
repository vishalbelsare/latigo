"""Client for connecting to the Metadata API."""
import logging

import requests_ms_auth
from requests import Response

logger = logging.getLogger(__name__)


class MetadataAPIClient:
    """Use for sending fetching and saving data to the Metadata API with APIM.

    Note:
        To use client: 'auto_adding_headers' in config should has 'Ocp-Apim-Subscription-Key' header with proper key.
    """

    def __init__(self, config: dict):
        self.auth_config = None
        self.base_url = None
        self.session = None
        self.config = config
        self._parse_auth_config()
        self._parse_base_url()
        self._create_session()  # session should be created last

    def _parse_auth_config(self):
        """Save 'auth_config' to the instance from the passed config."""

        self.auth_config = self.config.get("auth", dict())
        if not self.auth_config:
            return self._raise_exception("No 'auth' found in config")

        # Metadata API requires АРІМ headers to be passed on each request
        if not self.auth_config.get("auto_adding_headers", False):
            return self._raise_exception("'auto_adding_headers' should be passed in the 'auth' for APIM requests")

    def _parse_base_url(self):
        """Save 'base_url' to the instance from the passed config."""
        self.base_url = self.config.get("base_url", None)
        if not self.base_url:
            return self._raise_exception("No base_url found in config")

    def _create_session(self, force: bool = False):
        """Create session for the future calls."""
        if not self.session or force:
            self.session = requests_ms_auth.MsRequestsSession(
                requests_ms_auth.MsSessionConfig(**self.auth_config)
            )
        if not self.session:
            return self._raise_exception(f"Could not create session for {self.__class__.__name__}")

    @staticmethod
    def _raise_exception(message: str, exception_type=Exception) -> None:
        """Raise passed exception type with the message. Write message to the error log."""
        logger.error(message)
        raise exception_type(message)

    def get(self, *args, **kwargs) -> Response:
        """Make GET call the the API. Standard params are allowed."""
        res = self.session.get(*args, **kwargs)
        return res

    def post(self, *args, **kwargs) -> Response:
        """Make POST call the the API. Standard params are allowed."""
        res = self.session.post(*args, **kwargs)
        return res
