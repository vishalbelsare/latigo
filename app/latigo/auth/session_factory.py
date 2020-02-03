import typing
import sys
import logging
import adal


from requests_oauthlib import OAuth2Session


from .session import *


logger = logging.getLogger(__name__)


def fetch_access_token(auth_config: dict):
    client_id = auth_config.get("client_id")
    client_secret = auth_config.get("client_secret")
    tenant = auth_config.get("tenant", "adfs")
    validate_authority = tenant != "adfs"
    authority_host_url = auth_config.get(
        "authority_host_url", "https://login.microsoftonline.com"
    )
    authority_uri = f"{authority_host_url}/{tenant}"
    resource_uri = auth_config.get("resource", "https://management.core.windows.net/")
    token = None
    oathlib_token = None
    try:
        context = adal.AuthenticationContext(
            authority=authority_uri,
            validate_authority=validate_authority,
            api_version=None,
        )
        token = (
            context.acquire_token_with_client_credentials(
                resource_uri, client_id, client_secret
            )
            or {}
        )
        if token:
            # print("Got auth token:")
            # print(json.dumps(token, indent=2))
            # logger.info("fetch_access_token:")
            oathlib_token = {
                "access_token": token.get("accessToken", ""),
                "refresh_token": token.get("refreshToken", ""),
                "token_type": token.get("tokenType", "Bearer"),
                "expires_in": token.get("expiresIn", 0),
            }
            # logger.info(pprint.pformat(token))
        else:
            logger.error(f"Could not get token for client {authority_uri}")
    except Exception as e:
        logger.info(f"client_id:            {client_id}")
        logger.info(f"tenant:               {tenant}")
        logger.info(f"validate_authority:   {validate_authority}")
        logger.info(f"authority_host_url:   {authority_host_url}")
        logger.info(f"authority_uri:        {authority_uri}")
        logger.error(f"Error fetching token: {e}")
        raise e
    return oathlib_token


def token_saver(token):
    # logger.info("TOKEN SAVER SAVING:")
    # logger.info(pprint.pformat(token))
    # TODO: Find out if we really need this
    pass


def create_auth_session(auth_config: dict):

    # If any auth element values populated or empty, log error and exit
    if any([value is None for value in auth_config.values()]):
        logger.error(f"`Required elements in `auth_config` are missing.")
        sys.exit(1)

    client_id = auth_config.get("client_id")
    client_secret = auth_config.get("client_secret")
    authority_host_url = auth_config.get("authority_host_url")
    tenant = auth_config.get("tenant")
    scope = auth_config.get("scope", ["read", "write"])
    token_url = f"{authority_host_url}/{tenant}"
    extra = {"client_id": client_id, "client_secret": client_secret}
    session = None
    token = fetch_access_token(auth_config)
    if token:
        try:
            # session = OAuth2Session(client=client)
            session = LatigoAuthSession(auth_config=auth_config)
            # logger.info(f"Authenticated successfully with token:")
            # logger.info(token)
            # logger.info(f"Authenticated successfully with session:")
            # logger.info(session)
        except Exception as e:
            logger.error(f"Error creating LatigoAuthSession: {e}")
            raise e
    return session
