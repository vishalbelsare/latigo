from unittest.mock import Mock, patch

import pytest

from latigo.metadata_api.client import MetadataAPIClient


@pytest.fixture
@patch("latigo.metadata_api.client.MetadataAPIClient._create_session", new=Mock())
def metadata_api_client(config):
    return MetadataAPIClient(config.get("prediction_metadata_storage"))
