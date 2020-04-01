import logging
import pprint
from typing import Dict, Tuple

from latigo.types import PredictionDataSet

logger = logging.getLogger(__name__)


class MetadataStorageProviderInterface:
    def put_prediction_metadata(
        self,
        prediction_data: PredictionDataSet,
        output_tag_names: Dict[Tuple[str, str], str],
        output_time_series_ids: Dict[Tuple[str, str], str],
        input_time_series_ids: Dict[str, str],
    ):
        """Store the prediction metadata data."""
        raise NotImplementedError()


class MockMetadataStorageProvider(MetadataStorageProviderInterface):
    def __init__(self, config: dict):
        self.config = config

    def put_prediction_metadata(
        self,
        prediction_data: PredictionDataSet,
        output_tag_names: Dict[Tuple[str, str], str],
        output_time_series_ids: Dict[Tuple[str, str], str],
        input_time_series_ids: Dict[str, str],
    ):
        """Store the prediction metadata."""
        logger.info("MOCK STORING PREDICTIONS METADATA.")
        logger.info(pprint.pformat(prediction_data))


class DevNullMetadataStorageProvider(MetadataStorageProviderInterface):
    def __init__(self, config: dict):
        self.config = config

    def put_prediction_metadata(
        self,
        prediction_data: PredictionDataSet,
        output_tag_names: Dict[Tuple[str, str], str],
        output_time_series_ids: Dict[Tuple[str, str], str],
        input_time_series_ids: Dict[str, str],
    ):
        """Don't store the prediction metadata on purpose."""
        if self.config.get("do_log", False):
            logger.info(f"Skipping storing the  prediction metadata.")


def prediction_metadata_storage_provider_factory(config):
    provider_type = config.get("type", None)

    if "metadata_api" == provider_type:
        from latigo.metadata_api.metadata_storage_provider import MetadataAPIMetadataStorageProvider

        provider = MetadataAPIMetadataStorageProvider(config)
    elif "mock" == provider_type:
        provider = MockMetadataStorageProvider(config)
    else:
        provider = DevNullMetadataStorageProvider(config)
    return provider
