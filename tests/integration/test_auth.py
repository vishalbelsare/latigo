import typing
import logging
import pprint
from datetime import datetime, timedelta
from os import environ
from latigo.utils import datetime_from_rfc3339
from latigo.auth import *
from requests_oauthlib import OAuth2Session
import inspect


logger = logging.getLogger(__name__)


def _get_config():
    not_found = "Not found in environment variables"
    # fmt: off
    return {
            "url": environ.get("LATIGO_TIME_SERIES_BASE_URL", not_found),
            "resource": environ.get("LATIGO_TIME_SERIES_RESOURCE", not_found),
            "tenant": environ.get("LATIGO_TIME_SERIES_TENANT", not_found),
            "authority_host_url": environ.get("LATIGO_TIME_SERIES_AUTH_HOST_URL", not_found),
            "client_id": environ.get("LATIGO_TIME_SERIES_CLIENT_ID", not_found),
            "client_secret": environ.get("LATIGO_TIME_SERIES_CLIENT_SECRET", not_found)
    }
    # fmt: on


def test_auth_verifier():
    config = _get_config()
    url = config.get("url", "no-url-in-config")
    av = AuthVerifier(config=config)
    res, message = av.test_auth(url)
    if not res:
        logger.warning(f"Config was:")
        logger.warning(pprint.pformat(config))
        logger.warning(f"Message was: '{message}'")
    assert res


def test_session_signatures():
    assert inspect.signature(OAuth2Session) == inspect.signature(LatigoAuthSession)
    assert inspect.signature(OAuth2Session.__init__) == inspect.signature(LatigoAuthSession.__init__)
    oas2 = OAuth2Session()
    las = LatigoAuthSession()
    assert inspect.signature(oas2.request) == inspect.signature(las.request)
