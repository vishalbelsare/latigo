import logging
import pprint
from os import environ
from latigo.gordo import GordoModelInfoProvider, allocate_gordo_client_instances, gordo_client_instances_by_hash, gordo_client_instances_by_project, gordo_client_auth_session, gordo_config_hash, clean_gordo_client_args

logger = logging.getLogger(__name__)

def _get_config():
    not_found = "Not found in environment variables"
    # fmt: off
    return {
        "projects": ['ioc-98'],
        "connection_string": environ.get("LATIGO_GORDO_CONNECTION_STRING", not_found),
        "batch_size": 1000,
        "parallelism": 10,
        "forward_resampled_sensors": False,
        "ignore_unhealthy_targets": True,
        "n_retries": 5,
        "auth": {
            "resource": environ.get("LATIGO_GORDO_RESOURCE", not_found),
            "tenant": environ.get("LATIGO_GORDO_TENANT", not_found),
            "authority_host_url": environ.get("LATIGO_GORDO_AUTH_HOST_URL", not_found),
            "client_id": environ.get("LATIGO_GORDO_CLIENT_ID", not_found),
            "client_secret": environ.get("LATIGO_GORDO_CLIENT_SECRET", not_found)
        }
    }
    # fmt: on

def test_gordo_config_hash():
    hash=gordo_config_hash(
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
    clean_ok=clean_gordo_client_args(ok)
    assert clean_ok == ok
    bad = {**ok}
    bad['bad']='bad'
    clean_bad=clean_gordo_client_args(bad)
    assert clean_bad != bad
    
def test_client_instances():
    config = _get_config()
    logger.info("CONFIG:")
    logger.info(pprint.pformat(config))
    allocate_gordo_client_instances(config)
    logger.info(pprint.pformat(gordo_client_instances_by_hash))
    logger.info(pprint.pformat(gordo_client_instances_by_project))
    logger.info(pprint.pformat(gordo_client_auth_session))
    
def test_model_info():
    config = _get_config()
    logger.info("CONFIG:")
    logger.info(pprint.pformat(config))
    gordo_model_info_provider = GordoModelInfoProvider(config)
    filter={
        'projects':['ioc-98']
    }
    models = gordo_model_info_provider.get_models(filter)
    logger.info("MODELS:"+pprint.pformat(models))
