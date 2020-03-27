import typing
import logging
import math
import requests
import datetime
import json
import pprint
from requests.exceptions import HTTPError
import pandas as pd
import urllib.parse
from oauthlib.oauth2.rfc6749.errors import MissingTokenError

from latigo.types import (
    Task,
    SensorDataSpec,
    SensorDataSet,
    TimeRange,
    PredictionDataSet,
    LatigoSensorTag,
)
from latigo.intermediate import IntermediateFormat
from latigo.sensor_data import SensorDataProviderInterface
from latigo.prediction_storage import PredictionStorageProviderInterface
from latigo.utils import rfc3339_from_datetime
import requests_ms_auth

from .misc import invalid_operations, prediction_data_naming_convention
from .client import TimeSeriesAPIClient


logger = logging.getLogger(__name__)


def _x_in_data(res, x):
    if not isinstance(res, dict):
        return None
    data = res.get("data", {})
    if not isinstance(data, dict):
        return None
    items = data.get("items", [])
    if not isinstance(items, list):
        return None
    if len(items) < 1:
        return None
    item = items[0]
    if not isinstance(item, dict):
        return None
    return item.get(x, None)


def _id_in_data(res):
    return _x_in_data(res, "id")


class TimeSeriesAPIPredictionStorageProvider(
    TimeSeriesAPIClient, PredictionStorageProviderInterface
):
    def __init__(self, config: dict):
        super().__init__(config)

    def __str__(self):
        return f"TimeSeriesAPIPredictionStorageProvider({self.base_url})"

    def put_prediction(self, prediction_data: PredictionDataSet):
        """Store prediction data in time series api.

        Raises:
            Exception: if more then one prediction in "prediction_data.data" were passed.
        """
        data = prediction_data.data
        if not data:
            logger.warning("No prediction data for storing")
            return None
        if len(data) > 1:
            raise Exception(f"Only one prediction could be passed for storing, but passed - '{len(data)}'")

        output_tag_names: typing.Dict[typing.Tuple[str, str], str] = {}
        output_time_series_ids: typing.Dict[typing.Tuple[str, str], str] = {}
        row = data[0]
        df = row[1]
        model_name = prediction_data.meta_data.model_name

        for col in df.columns:
            output_tag_name = prediction_data_naming_convention(
                operation=col[0], model_name=model_name, tag_name=col[1]
            )
            if not output_tag_name:
                continue
            output_time_series_ids[col] = ""
            description = f"Gordo prediction for {col[0]} - {col[1]}"
            # Units cannot be derrived easily. Should be provided by prediction execution provider or set to none
            unit = ""
            # TODO: Should we generate some external_id?
            external_id = ""
            meta, err = self._create_id_if_not_exists(
                name=output_tag_name,
                description=description,
                unit=unit,
                external_id=external_id,
            )
            if not meta and not err:
                err = "Meta mising with no error"
            if err:
                logger.error(f"Could not create/find id for name {output_tag_name}: {err}")
                continue
            id = _id_in_data(meta)
            if not id:
                logger.error(f"Could not get ID for {output_tag_name}")
                continue
            output_tag_names[col] = output_tag_name
            output_time_series_ids[col] = id
        failed_tags = 0
        stored_tags = 0
        skipped_values = 0
        stored_values = 0
        logger.info(f"Storing {len(df.columns)} predictions:")
        for key, item in df.items():
            operation, tag_name = key
            if operation in invalid_operations:
                continue
            datapoints = []
            id = output_time_series_ids[key]
            # logger.info(f"Key({key}) id={id}")
            for time, value in item.items():
                stored_values += 1
                # logger.info(f"  Item({time}, {value})")
                if math.isnan(value):
                    # logger.info(f"Skipping NaN value for {key} @ {time}")
                    skipped_values += 1
                    continue
                datapoints.append(
                    {"time": rfc3339_from_datetime(time), "value": value, "status": "0"}
                )
            res, err = self._store_data_for_id(id=id, datapoints=datapoints)
            if not res or err:
                logger.error(f" Could not store data: {err}")
                failed_tags += 1
            else:
                stored_tags += 1
        logger.info(
            f"  {stored_values} values stored, {skipped_values} NaNs skipped. {stored_tags} tags stored, {failed_tags} tags failed"
        )
        # with pd.option_context("display.max_rows", None, "display.max_columns", None):
        #    logger.info("")
        #    logger.info(f"  Item({item})")

        return None
