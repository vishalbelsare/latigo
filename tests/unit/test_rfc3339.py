import logging
import pprint
import os
import datetime
from latigo.utils import merge, load_config, load_yaml, save_yaml, rfc3339_from_datetime, datetime_from_rfc3339
import latigo.rfc3339

logger = logging.getLogger(__name__)


def test_to_from_datetime():
    date_object = datetime.datetime(2001, 1, 1, 1, 1, 1, 1000, tzinfo=latigo.rfc3339.tzinfo(-83, "-01:23"))
    date_string = rfc3339_from_datetime(date_object)
    logger.info(date_string)
    assert date_object == datetime_from_rfc3339(date_string)


def test_seconds_resolution():
    date_object = datetime.datetime(2001, 1, 1, 1, 1, 1, 0, tzinfo=latigo.rfc3339.UTC_TZ)
    date_string = rfc3339_from_datetime(date_object)
    logger.info(date_string)
    for date_string in ["2001-01-01T01:01:01.000000Z", "2001-01-01T01:01:01.00000Z", "2001-01-01T01:01:01.0000Z", "2001-01-01T01:01:01.000Z", "2001-01-01T01:01:01.00Z", "2001-01-01T01:01:01.0Z", "2001-01-01T01:01:01Z"]:
        assert date_object == datetime_from_rfc3339(date_string)
