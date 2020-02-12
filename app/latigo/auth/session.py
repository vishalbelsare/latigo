import adal
import json
import logging
import oauthlib.oauth2
import os
import pprint
import random
import requests
import requests_oauthlib
import string
import sys
import time
import typing
import uuid
import inspect

from requests_oauthlib import OAuth2Session

from oauthlib.oauth2 import BackendApplicationClient

## AADTokenCredentials for multi-factor authentication
from msrestazure.azure_active_directory import AADTokenCredentials

## Required for Azure Data Lake Analytics job management
from azure.mgmt.datalake.analytics.job import DataLakeAnalyticsJobManagementClient
from azure.mgmt.datalake.analytics.job.models import (
    JobInformation,
    JobState,
    USqlJobProperties,
)

from urllib3.exceptions import NewConnectionError


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
        self.latigo_auth_config = auth_config
        self.latigo_client_id = self.latigo_auth_config.get("client_id")
        self.latigo_client_secret = self.latigo_auth_config.get("client_secret")
        self.latigo_resource_uri = self.latigo_auth_config.get(
            "resource", "https://management.core.windows.net/"
        )
        self.latigo_authority_host_url = self.latigo_auth_config.get(
            "authority_host_url", "https://login.microsoftonline.com"
        )
        self.latigo_tenant = self.latigo_auth_config.get("tenant", "adfs")
        self.latigo_validate_authority = self.latigo_tenant != "adfs"
        self.latigo_scope = self.latigo_auth_config.get("scope", ["read", "write"])
        self.latigo_redirect_uri = self.latigo_auth_config.get("verification_url")
        self.latigo_auto_refresh_url = (
            f"{self.latigo_authority_host_url}/{self.latigo_tenant}"
        )
        self.latigo_auto_refresh_kwargs = {
            "client_id": self.latigo_client_id,
            "client_secret": self.latigo_client_secret,
            "resource": self.latigo_resource_uri,
        }  # aka extra
        self.latigo_state = None
        self.latigo_token = self._fetch_access_token()
        # client=requests_oauthlib.WebApplicationClient(client_id=self.latigo_client_id, token=self.latigo_token)
        self.latigo_client = oauthlib.oauth2.BackendApplicationClient(
            client_id=self.latigo_client_id,
            token=self.latigo_token,
            auto_refresh_url=self.latigo_auto_refresh_url,
            auto_refresh_kwargs=self.latigo_auto_refresh_kwargs,
            token_updater=self._token_saver,
            scope=self.latigo_scope,
        )

        logging.info(
            f"@@@ Latigo Session: __init__(client_id={self.latigo_client_id}, auto_refresh_url={self.latigo_auto_refresh_url}, scope={self.latigo_scope}, redirect_uri={self.latigo_redirect_uri})."
        )
        super(LatigoAuthSession, self).__init__(
            #            client_id=self.latigo_client_id,
            client=self.latigo_client,
            token=self.latigo_token,
            #            auto_refresh_url=self.latigo_auto_refresh_url,
            #            auto_refresh_kwargs=self.latigo_auto_refresh_kwargs,
            #            scope=self.latigo_scope,
            #            redirect_uri=self.latigo_redirect_uri,
            #            token=self.latigo_token,
            #            state=self.latigo_state,
            #            token_updater=self._token_saver,
            #            **kwargs,
        )
        self.verify_auth()

    def _fetch_access_token(self):
        self.latigo_adal_token = None
        self.latigo_oathlib_token = None
        try:
            context = adal.AuthenticationContext(
                authority=self.latigo_auto_refresh_url,
                validate_authority=self.latigo_validate_authority,
                api_version=None,
            )
            self.latigo_adal_token = (
                context.acquire_token_with_client_credentials(
                    self.latigo_resource_uri,
                    self.latigo_client_id,
                    self.latigo_client_secret,
                )
                or {}
            )
            if self.latigo_adal_token:
                self.latigo_oathlib_token = {
                    "access_token": self.latigo_adal_token.get("accessToken", ""),
                    "refresh_token": self.latigo_adal_token.get("refreshToken", ""),
                    "token_type": self.latigo_adal_token.get("tokenType", "Bearer"),
                    "expires_in": self.latigo_adal_token.get("expiresIn", 0),
                }
            else:
                logger.error(
                    f"Could not get token for client {self.latigo_auto_refresh_url}"
                )
        except Exception as e:
            logger.error(f"Error fetching token: {e}", exc_info=True)
            logger.warning(
                "NOTE:\n"
                + f"client_id:            {self.latigo_client_id}\n"
                + f"tenant:               {self.latigo_tenant}\n"
                + f"validate_authority:   {self.latigo_validate_authority}\n"
                + f"authority_host_url:   {self.latigo_authority_host_url}\n"
                + f"auto_refresh_url:     {self.latigo_auto_refresh_url}\n"
            )
            raise e
        return self.latigo_oathlib_token

    def _token_saver(self, token):
        logger.info("@@@ Latigo Session: TOKEN SAVER SAVING:")
        logger.info(pprint.pformat(token))
        pass

    def verify_auth(self) -> typing.Tuple[bool, typing.Optional[str]]:
        try:
            url = self.latigo_auth_config.get("verification_url")
            if url:
                logger.info(
                    "@@@ Latigo Session: Verification URL specified, performing verification"
                )
                res = self.get(url)
                if None == res:
                    raise Exception("No response object returned")
                if not res:
                    res.raise_for_status()
            else:
                logger.info(
                    f"@@@ Latigo Session: No verification URL specified in {pprint.pformat(self.latigo_auth_config)}, skipping verification"
                )
        except Exception as e:
            # Failure
            raise e
            return False, f"{e}"
        # Success
        return True, None

    def prepare_request(self, request):
        logging.info(
            f"@@@ Latigo Session: prepare_request(method={request.method}, url='{request.url}')."
        )
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
        return super(LatigoAuthSession, self).request(
            method=method,
            url=url,
            data=data,
            headers=headers,
            withhold_token=withhold_token,
            client_id=client_id,
            client_secret=client_secret,
            **kwargs,
        )

    def send(self, request, **kwargs):
        logging.info(
            f"@@@ Latigo Session: send(method={request.method}, url='{request.url}')."
        )
        try:
            response = super(LatigoAuthSession, self).send(request, **kwargs)
            logging.info(
                f"@@@ Latigo Session: Response head follows: -----------------------"
            )
            logging.info(response.content[0:200])
            return response
        except NewConnectionError as nce:
            logger.error(f"Could not connect (method={method}, url='{url}'): {nce}")
        except requests.exceptions.HTTPError as he:
            logger.error(f"HTTP STATUS CODE WAS: {he}")
        except Exception as e:
            logger.error(
                f"Could not perform request(method={method}, url='{url}'): {e}",
                exc_info=True,
            )
        return None

    def close(self):
        logging.info(f"@@@ Latigo Session: close().")
        return super(LatigoAuthSession, self).close()
