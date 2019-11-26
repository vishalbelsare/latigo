import logging
import pprint
from os import environ
from latigo.gordo import GordoModelInfoProvider, LatigoDataProvider, LatigoPredictionForwarder, allocate_gordo_client_instances, clean_gordo_client_args, expand_gordo_connection_string, expand_gordo_data_provider, expand_gordo_prediction_forwarder, gordo_client_auth_session, gordo_client_instances_by_hash, gordo_client_instances_by_project, gordo_config_hash


def test_gordo_config_hash():
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
    logger.info(hash)
    assert "gordoschemeAhostBport8080projectDtargetEgordo_versionFbatch_sizeGparallelismHforward_resampled_sensorsIignore_unhealthy_targetsJn_retriesK" == hash


def test_clean_gordo_client_args():
    # fmt: off
    ok={
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
    clean_ok = clean_gordo_client_args(ok)
    assert clean_ok == ok
    bad = {**ok}
    bad["bad"] = "bad"
    clean_bad = clean_gordo_client_args(bad)
    assert clean_bad != bad


def test_expand_gordo_data_provider():
    config = {"data_provider": {"debug": True, "n_retries": 5}}
    expand_gordo_data_provider(config, "OK")
    assert isinstance(config.get("data_provider", None), LatigoDataProvider)


def test_expand_gordo_prediction_forwarder():
    config = {"prediction_forwarder": {"debug": True, "n_retries": 5}}
    expand_gordo_prediction_forwarder(config, "OK")
    assert isinstance(config.get("prediction_forwarder", None), LatigoPredictionForwarder)
