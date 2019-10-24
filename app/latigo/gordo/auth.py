import json
import os
import random
import string
import sys
import json
import logging
import os
import sys
import adal


def get_bearer_token(auth_config):
    authority_url = f"{auth_config['authority_host_url']}/{auth_config['tenant']}"
    resource = auth_config.get("resource", "00000002-0000-0000-c000-000000000000")
    validate_authority = auth_config.get("tenant", "adfs") != "adfs"
    context = adal.AuthenticationContext(authority_url, validate_authority=validate_authority)
    token = context.acquire_token_with_client_credentials(resource, auth_config["client_id"], auth_config["client_secret"])
    print("Here is the token:")
    print(json.dumps(token, indent=2))
    return token
