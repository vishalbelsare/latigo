import logging
import pprint
from os import environ
from latigo.gordo import (
    GordoModelInfoProvider,
    LatigoDataProvider,
    LatigoPredictionForwarder,
    GordoClientPool,
    clean_gordo_client_args,
    expand_gordo_connection_string,
    expand_gordo_data_provider,
    expand_gordo_prediction_forwarder,
    _gordo_to_latigo_tag_list,
    _gordo_to_latigo_tag,
)
from gordo.machine.dataset.sensor_tag import SensorTag
from latigo.types import LatigoSensorTag


def un_test_gordo_config_hash():
    hash = gordo_config_hash(
        # fmt: off
    {
        "scheme":"A",
        "host":"B",
        "port":8080,
        "project":"D",
        "target":"E",
        "gordo_version":"F",
        "batch_size":"G",
        "parallelism":"H",
        "forward_resampled_sensors":"I",
        "ignore_unhealthy_targets":"J",
        "n_retries":"K"
    }
        # fmt: on
    )
    # logger.info(hash)
    assert (
        "gordoschemeAhostBport8080projectDtargetEgordo_versionFbatch_sizeGparallelismHforward_resampled_sensorsIignore_unhealthy_targetsJn_retriesK"
        == hash
    )


def un_test_gordo_client_pool():
    # GordoClientPool
    pass


def test_clean_gordo_client_args():
    # fmt: off

    ok={
        'scheme': 'A',
        'host': 'B',
        'port': 8080,
        'project': 'D',
        'target': 'E',
        'gordo_version': 'F',
        'batch_size': 'G',
        'parallelism': 'H',
        'forward_resampled_sensors': 'I',
        'n_retries': 5,
        'metadata': 'L',
        'data_provider': 'M',
        'prediction_forwarder': 'N',
        'session': 'O',
        'use_parquet': 'P'
    }
    # fmt: on
    clean_ok = clean_gordo_client_args(ok)
    assert clean_ok == ok
    bad = {**ok}
    bad["bad"] = "bad"
    clean_bad = clean_gordo_client_args(bad)
    assert clean_bad != bad


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
    latigo_tag_list = _gordo_to_latigo_tag_list(gordo_tag_list)


def un_test_expand_gordo_data_provider():
    config = {"data_provider": {"debug": True, "n_retries": 5}}
    expand_gordo_data_provider(config, "OK")
    assert isinstance(config.get("data_provider", None), LatigoDataProvider)


def un_test_expand_gordo_prediction_forwarder():
    config = {"prediction_forwarder": {"debug": True, "n_retries": 5}}
    expand_gordo_prediction_forwarder(config, "OK")
    assert isinstance(
        config.get("prediction_forwarder", None), LatigoPredictionForwarder
    )
