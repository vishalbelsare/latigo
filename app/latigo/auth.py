from typing import List, Optional, Dict
from requests_ms_auth import MsRequestsSession, MsSessionConfig


# Helper to perform auth check given a list of auth configs
def auth_check(auth_configs: List[Optional[Dict]]):
    for auth_config in auth_configs:
        if auth_config:
            auth_config["verify_on_startup"] = False
            auth_session = MsRequestsSession(MsSessionConfig(**auth_config))
            return auth_session.verify_auth() + (auth_session,)
    return True, None, None
