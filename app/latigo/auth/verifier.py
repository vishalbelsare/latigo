import pprint
import typing
import logging

import requests_ms_auth

logger = logging.getLogger(__name__)


class AuthVerifier:
    def __init__(self, config: typing.Dict):
        self.config = config

    def test_auth(self, url: str) -> typing.Tuple[bool, typing.Optional[str]]:
        try:
            self.auth_session = requests_ms_auth.MsRequestsSession(
                requests_ms_auth.MsSessionConfig(**self.config)
            )
            res = self.auth_session.get(url)
            if None == res:
                raise Exception("No response object returned")
            if not res:
                res.raise_for_status()
        except Exception as e:
            # Failure
            # raise e
            return False, f"{e} ({url})"
        # Success
        return True, None


class AuthVerifyList:
    def __init__(self, name: str):
        self.name = name
        self.verifiers: typing.Dict[str, typing.Tuple[str, AuthVerifier]] = {}

    def register_verification(self, url: str, config: dict):
        key = url + pprint.pformat(dict)
        # Don't insert duplicate entries
        if key in self.verifiers:
            return
        self.verifiers[key] = (url, AuthVerifier(config=config))

    def verify(self):
        error_count = 0
        for key, tup in self.verifiers.items():
            url, verifier = tup
            res, message = verifier.test_auth(url=url)
            if not res:
                logger.error(f"Auth test for '{url}' failed with: '{message}'")
                error_count += 1
        if error_count > 0:
            return (
                False,
                f"Auth test failed for {error_count} of {len(self.verifiers)} configurations, see previous logs for details.",
            )
        else:
            return (
                True,
                f"Auth test succeedded for all {len(self.verifiers)} configurations.",
            )
