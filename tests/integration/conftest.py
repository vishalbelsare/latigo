from os import environ

from pytest import fixture

from latigo.metadata_api.client import MetadataAPIClient

METADATA_API_TENANT = environ["METADATA_API_TENANT"]
METADATA_API_CLIENT_ID = environ["METADATA_API_CLIENT_ID"]
METADATA_API_CLIENT_SECRET = environ["METADATA_API_CLIENT_SECRET"]
METADATA_API_RESOURCE = environ["METADATA_API_RESOURCE"]
METADATA_API_AUTHORITY_HOST_URL = environ["METADATA_API_AUTHORITY_HOST_URL"]
METADATA_API_BASE_URL = environ["METADATA_API_BASE_URL"]
METADATA_API_APIM_KEY = environ["METADATA_API_APIM_KEY"]
METADATA_API_APIM_HEADER = "Ocp-Apim-Subscription-Key"


@fixture(scope="function")
def metadata_integration_auth():
    return {
        "tenant": METADATA_API_TENANT,
        "client_id": METADATA_API_CLIENT_ID,
        "client_secret": METADATA_API_CLIENT_SECRET,
        "resource": METADATA_API_RESOURCE,
        "authority_host_url": METADATA_API_AUTHORITY_HOST_URL,
        "auto_adding_headers": {METADATA_API_APIM_HEADER: METADATA_API_APIM_KEY},
    }


@fixture(scope="function")
def metadata_integration_api_config(metadata_integration_auth):
    return {
        "type": "metadata_api",
        "base_url": METADATA_API_BASE_URL,
        "auth": metadata_integration_auth,
    }


@fixture(scope="function")
def metadata_client(metadata_integration_api_config) -> MetadataAPIClient:
    client = MetadataAPIClient(metadata_integration_api_config)
    return client
