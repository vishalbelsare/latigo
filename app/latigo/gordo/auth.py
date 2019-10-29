import json
import os
import random
import string
import sys
import json
import logging
import pprint
import os
import sys
import adal


from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import BackendApplicationClient


## AADTokenCredentials for multi-factor authentication
from msrestazure.azure_active_directory import AADTokenCredentials

## Required for Azure Data Lake Analytics job management
from azure.mgmt.datalake.analytics.job import DataLakeAnalyticsJobManagementClient
from azure.mgmt.datalake.analytics.job.models import JobInformation, JobState, USqlJobProperties

## Other required imports
import adal, uuid, time

logger = logging.getLogger(__name__)

# TODO: Merge with fetch_access_token()
def get_bearer_token(auth_config):
    authority_url = f"{auth_config['authority_host_url']}/{auth_config['tenant']}"
    resource = auth_config.get("resource", "00000002-0000-0000-c000-000000000000")
    validate_authority = auth_config.get("tenant", "adfs") != "adfs"
    token = None
    try:
        context = adal.AuthenticationContext(authority_url, validate_authority=validate_authority)
        token = context.acquire_token_with_client_credentials(resource, auth_config["client_id"], auth_config["client_secret"])
        print("Here is the token:")
        print(json.dumps(token, indent=2))
    except Exception as e:
        logger.error(f"Error fetching token: {e}")
    return token


def fetch_access_token(auth_config: dict):
    client_id = auth_config.get("client_id")
    client_secret = auth_config.get("client_secret")
    authority_host_url = auth_config.get("authority_host_url")
    tenant = auth_config.get("tenant")
    authority_host_uri = "https://login.microsoftonline.com"
    authority_uri = f"{authority_host_url}/{tenant}"
    resource_uri = "https://management.core.windows.net/"
    token = None
    oathlib_token = None
    try:
        context = adal.AuthenticationContext(authority_uri, api_version=None)
        token = context.acquire_token_with_client_credentials(resource_uri, client_id, client_secret) or {}
        if token:
            # logger.info("fetch_access_token:")
            oathlib_token = {"access_token": token.get("accessToken", ""), "refresh_token": token.get("refreshToken", ""), "token_type": token.get("tokenType", "Bearer"), "expires_in": token.get("expiresIn", 0)}
            # logger.info(pprint.pformat(token))
    except Exception as e:
        logger.error(f"Error fetching token: {e}")
    return oathlib_token


def token_saver(token):
    # logger.info("TOKEN SAVER SAVING:")
    # logger.info(pprint.pformat(token))
    # TODO: Find out if we really need this
    pass


def create_auth_session(auth_config: dict):
    client_id = auth_config.get("client_id")
    client_secret = auth_config.get("client_secret")
    authority_host_url = auth_config.get("authority_host_url")
    tenant = auth_config.get("tenant")
    token_url = f"{authority_host_url}/{tenant}"
    extra = {"client_id": client_id, "client_secret": client_secret}
    refresh_url = "https://login.microsoftonline.com"
    session = None
    token = fetch_access_token(auth_config)
    if token:
        try:
            session = OAuth2Session(auth_config.get("client_id"), token=token, auto_refresh_url=token_url, auto_refresh_kwargs=extra, token_updater=token_saver)
        except Exception as e:
            logger.error(f"Error creating OAuth2Session: {e}")
    return session
