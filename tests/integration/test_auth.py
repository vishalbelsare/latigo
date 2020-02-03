import typing
import logging
import pprint
from os import environ
import latigo.utils
import latigo.auth
from requests_oauthlib import OAuth2Session
import inspect

import time
import datetime


logger = logging.getLogger(__name__)


def _get_config(type="time_series"):
    not_found = "Not found in environment variables"
    if type == "gordo":
        # fmt: off
        return {
                "verification_url": environ.get("LATIGO_GORDO_CONNECTION_STRING", not_found)+'/ioc-1901/models',
                "url": environ.get("LATIGO_GORDO_CONNECTION_STRING", not_found),
                "resource": environ.get("LATIGO_GORDO_RESOURCE", not_found),
                "tenant": environ.get("LATIGO_GORDO_TENANT", not_found),
                "authority_host_url": environ.get("LATIGO_GORDO_AUTH_HOST_URL", not_found),
                "client_id": "INVALID_CLIENT_ID",#environ.get("LATIGO_GORDO_CLIENT_ID", not_found),
                "client_secret": "INVALID_CLIENT_SECRET",#environ.get("LATIGO_GORDO_CLIENT_SECRET", not_found)
        }
        # fmt: on
    elif type == "time_series":
        # fmt: off
        return {
                "verification_url": environ.get("LATIGO_TIME_SERIES_BASE_URL", not_found),
                "url": environ.get("LATIGO_TIME_SERIES_BASE_URL", not_found),
                "resource": environ.get("LATIGO_TIME_SERIES_RESOURCE", not_found),
                "tenant": environ.get("LATIGO_TIME_SERIES_TENANT", not_found),
                "authority_host_url": environ.get("LATIGO_TIME_SERIES_AUTH_HOST_URL", not_found),
                "client_id": environ.get("LATIGO_TIME_SERIES_CLIENT_ID", not_found),
                "client_secret": environ.get("LATIGO_TIME_SERIES_CLIENT_SECRET", not_found)
        }
        # fmt: on
    else:
        return {}


def _test_auth_verifier():
    config = _get_config()
    url = config.get("verification_url", "no-url-in-config")
    av = latigo.auth.verifier.AuthVerifier(config=config)
    res, message = av.test_auth(url)
    if not res:
        logger.warning(f"Config was:")
        logger.warning(pprint.pformat(config))
        logger.warning(f"Message was: '{message}'")
    assert res


def test_session_verifier():
    config = _get_config()
    session = latigo.auth.session.LatigoAuthSession(config)
    logger.info(pprint.pformat(config))
    logger.info(pprint.pformat(session))
    assert session
    res, message = session.verify_auth()
    if not res:
        logger.warning(f"Config was:")
        logger.warning(pprint.pformat(config))
        logger.warning(f"Message was: '{message}'")
    assert res


def test_session_signatures():
    assert inspect.signature(OAuth2Session.request) == inspect.signature(
        latigo.auth.session.LatigoAuthSession.request
    )


def test_session():
    config = _get_config(type="gordo")
    logger.info("Using config:")
    logger.info(pprint.pformat(config))
    session = latigo.auth.session.LatigoAuthSession(config)
    assert session
    i = 0
    start = datetime.datetime.now()
    while True:
        interval = datetime.datetime.now() - start
        i += 1
        logger.info(f"Run {i} @ {latigo.utils.human_delta(interval)}: -------")
        res = session.get(config.get("verification_url"))
        logger.info(pprint.pformat(res))
        if None == res:
            raise Exception("No response object returned")
        if not res:
            res.raise_for_status()
        assert res
        logger.info("")
        time.sleep(60)
