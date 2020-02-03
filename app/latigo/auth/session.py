import logging
import pprint
import typing

import requests_oauthlib
import oauthlib.oauth2

from urllib3.exceptions import NewConnectionError


import inspect


logger = logging.getLogger(__name__)


class LatigoAuthSession(requests_oauthlib.OAuth2Session):

    """
    A wrapper for OAuth2Session that allows us to do debugging and adal refresh among other things.
    See https://requests.readthedocs.io/en/latest/_modules/requests/sessions/#Session
    See https://requests-oauthlib.readthedocs.io/en/latest/api.html#oauth-2-0-session
    """

    def __init__(
        self,
        auth_config={},
        #        **kwargs,
    ):
        self.auth_config=auth_config
        client_id = self.auth_config.get("client_id")
        client_secret = self.auth_config.get("client_secret")
        resource = self.auth_config.get("resource")
        authority_host_url = self.auth_config.get("authority_host_url")
        tenant = self.auth_config.get("tenant")
        scope = self.auth_config.get("scope", ["read", "write"])
        redirect_uri = self.auth_config.get("verification_url")
        auto_refresh_url = (
            f"{authority_host_url}/{tenant}"
        )  # aka token_url # "https://login.microsoftonline.com"
        auto_refresh_kwargs = {
            "client_id": client_id,
            "client_secret": client_secret,
            "resource": resource,
        }  # aka extra
        state = None
        token_updater = None
        token = None
        # token = fetch_access_token(self.auth_config)
        # client=requests_oauthlib.WebApplicationClient(client_id=client_id, token=token)
        client = oauthlib.oauth2.BackendApplicationClient(
            client_id=client_id,
            token=token,
            auto_refresh_url=auto_refresh_url,
            auto_refresh_kwargs=auto_refresh_kwargs,
            token_updater=self._token_saver,
            scope=scope,
        )

        logging.info(
            f"@@@ Latigo Session: __init__(client_id={client_id}, auto_refresh_url={auto_refresh_url}, scope={scope}, redirect_uri={redirect_uri})."
        )
        super(LatigoAuthSession, self).__init__(
            #            client_id=client_id,
            client=client,
            #            auto_refresh_url=auto_refresh_url,
            #            auto_refresh_kwargs=auto_refresh_kwargs,
            #            scope=scope,
            #            redirect_uri=redirect_uri,
            #            token=token,
            #            state=state,
            #            token_updater=token_updater,
            #            **kwargs,
        )

    def _token_saver(token):
        logger.info("TOKEN SAVER SAVING:")
        logger.info(pprint.pformat(token))
        pass



    def verify_auth(self) -> typing.Tuple[bool, typing.Optional[str]]:
        try:
            url= self.auth_config.get("verification_url")
            res = self.get(url)
            if None == res:
                raise Exception("No response object returned")
            if not res:
                res.raise_for_status()
        except Exception as e:
            # Failure
            raise e
            return False, f"{e}"
        # Success
        return True, None


    def prepare_request(self, request):
        logging.info(f"@@@ Latigo Session: prepare_request(request={request}).")
        return super(LatigoAuthSession, self).prepare_request(request)

    def request(
        self,
        method,
        url,
        data=None,
        headers=None,
        withhold_token=False,
        client_id=None,
        client_secret=None,
        **kwargs,
    ):
        logging.info(f"@@@ Latigo Session: request(method={method}, url='{url}').")
        try:
            response = super(LatigoAuthSession, self).request(
                method=method,
                url=url,
                data=data,
                headers=headers,
                withhold_token=withhold_token,
                client_id=client_id,
                client_secret=client_secret,
                **kwargs,
            )
            return response
        except NewConnectionError as nce:
            logger.error(f"Could not connect (method={method}, url='{url}'): {nce}")
        except requests.exceptions.HTTPError as he:
            logger.error(f"HTTP STATUS CODE WAS: {he}")
        except Exception as e:
            logger.error(
                f"Could not perform request(method={method}, url='{url}'): {e}"
            )
        return None

    def send(self, request, **kwargs):
        logging.info(f"@@@ Latigo Session: send().")
        return super(LatigoAuthSession, self).send(request, **kwargs)

    def close(self):
        logging.info(f"@@@ Latigo Session: close().")
        return super(LatigoAuthSession, self).close()
