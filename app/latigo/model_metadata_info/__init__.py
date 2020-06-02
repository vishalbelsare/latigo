import logging
from typing import List

from latigo.metadata_api.client import MetadataAPIClient

logger = logging.getLogger(__name__)


class ModelMetadataInfoInterface:
    def get_projects(self) -> List[str]:
        """Get all unique projects/assets."""
        raise NotImplementedError()


class ModelMetadataInfo(MetadataAPIClient, ModelMetadataInfoInterface):
    pass


def model_metadata_info_factory(config) -> ModelMetadataInfo:
    model_metadata_info_provider = config.get("type", None)

    if "metadata_api" == model_metadata_info_provider:
        model_metadata_info = ModelMetadataInfo(config)
    else:
        raise ValueError(f"{model_metadata_info_provider} is not supported by 'model_metadata_info_factory'")
    return model_metadata_info
