import typing
import logging
import pprint
import os
import yaml
import latigo.utils
import latigo.auth
from requests_oauthlib import OAuth2Session
import inspect

import time
import datetime


logger = logging.getLogger(__name__)


def _get_config(type="time_series"):
    # Note: This file should be provided by the environment that conducts the test and never put into source control
    filename = "../executor_local.yaml"
    assert os.path.exists(filename)
    with open(filename, "r") as stream:
        data = {}
        failure = None
        data = yaml.safe_load(stream)
    if type == "gordo":
        return data["model_info"]["auth"]
    elif type == "time_series":
        return data["sensor_data"]["auth"]


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


def _test_session_verifier():
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


def _test_session_signatures():
    assert inspect.signature(OAuth2Session.request) == inspect.signature(
        latigo.auth.session.LatigoAuthSession.request
    )


def test_session():
    config = _get_config(type="time_series")
    logger.info("Using config:")
    logger.info(pprint.pformat(config))
    session = latigo.auth.session.LatigoAuthSession(auth_config=config)
    # session = sf(auth_config=config)
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
