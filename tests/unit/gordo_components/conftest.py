import pytest

from latigo.gordo import GordoModelInfoProvider


@pytest.fixture
def gordo_model_info_provider(config) -> GordoModelInfoProvider:
    return GordoModelInfoProvider(config.get("model_info"))
