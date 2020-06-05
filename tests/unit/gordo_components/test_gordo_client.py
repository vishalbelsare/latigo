from gordo.machine.dataset.sensor_tag import SensorTag

from latigo.gordo import clean_gordo_client_args, gordo_config_hash
from latigo.gordo.data_provider import _gordo_to_latigo_tag_list, _gordo_to_latigo_tag
from latigo.types import LatigoSensorTag


def test_gordo_config_hash():
    result_hash = gordo_config_hash(
        {
            "scheme": "A",
            "host": "B",
            "port": 8080,
            "project": "D",
            "target": "E",
            "gordo_version": "F",
            "batch_size": "G",
            "parallelism": "H",
            "forward_resampled_sensors": "I",
            "ignore_unhealthy_targets": "J",
            "n_retries": "K",
        }
    )
    assert (
        "gordoschemeAhostBport8080projectDbatch_sizeGparallelismHforward_resampled_sensorsIn_retriesKuse_parquet"
        == result_hash
    )


def test_clean_gordo_client_args():
    ok = {
        "scheme": "A",
        "host": "B",
        "port": 8080,
        "project": "D",
        "target": "E",
        "gordo_version": "F",
        "batch_size": "G",
        "parallelism": "H",
        "forward_resampled_sensors": "I",
        "n_retries": 5,
        "metadata": "L",
        "data_provider": "M",
        "prediction_forwarder": "N",
        "session": "O",
        "use_parquet": "P",
    }
    expected = {
        "project": "D",
        "host": "B",
        "port": 8080,
        "scheme": "A",
        "metadata": "L",
        "data_provider": "M",
        "prediction_forwarder": "N",
        "batch_size": "G",
        "parallelism": "H",
        "forward_resampled_sensors": "I",
        "n_retries": 5,
        "session": "O",
        "use_parquet": "P",
    }
    cleaned = clean_gordo_client_args(ok)
    assert cleaned == expected


def test_gordo_to_latigo_tag():
    name = "some_name"
    asset = "some_asset"
    gordo_tag = SensorTag(name=name, asset=asset)
    assert isinstance(gordo_tag, SensorTag)
    latigo_tag = _gordo_to_latigo_tag(gordo_tag)
    assert isinstance(latigo_tag, LatigoSensorTag)
    assert type(latigo_tag.name) == type(name)
    assert type(latigo_tag.asset) == type(asset)
    assert latigo_tag.name == name
    assert latigo_tag.asset == asset


def test_gordo_to_latigo_tag_list():
    name = "some_name"
    asset = "some_asset"
    gordo_tag_list = [SensorTag(name=name, asset=asset)]
    expected = [LatigoSensorTag(name, asset)]

    result_tag_list = _gordo_to_latigo_tag_list(gordo_tag_list)
    assert expected == result_tag_list
