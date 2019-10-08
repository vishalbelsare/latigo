#!/usr/bin/env python

from os import environ, path, system

from app.latigo.utils import load_yaml, save_yaml

pwd=path.dirname(path.realpath(__file__))

filename = pwd+"/local_config.yaml"

local_config = {}
failure = None


if not path.exists(filename):
    # Create a starting point for local config so that user can get quickly up
    # and running
    local_config["LATIGO_MESSAGE"] = f"YOUR LOCAL ENV CAN NOW BE EDITED IN {filename}. RE-RUN THIS SCRIPT TO LOAD ANY CHANGES"
    local_config["LATIGO_INTERNAL_EVENT_HUB"] = "GET YOUR EVENT_HUB CONNECTION STRING FROM AZURE PORTAL"
    local_config["LATIGO_INTERNAL_DATABASE"] = "THE CONNECTION STRING TO DATABASE"
    local_config["LATIGO_EXECUTOR_CONFIG_FILE"] = "THE LOCATION OF PREDICTION EXECUTOR CONFIG FILE IN YAML FORMAT"
    local_config["LATIGO_SCHEDULER_CONFIG_FILE"] = "THE LOCATION OF PREDICTION SCHEDULER CONFIG FILE IN YAML FORMAT"
    local_config["LATIGO_SENSOR_DATA_CONNECITON"] = "THE CONNECTION STRING FOR THE SENSOR DATA"
    local_config["LATIGO_PREDICTION_STORAGE_CONNECITON"] = "THE CONNECTION STRING FOR THE PREDICTION STORAGE"
    local_config["POSTGRES_PASSWORD"] = "Set a secure password for your local postgreSQL instance here"
    save_yaml(filename, local_config)
else:
    local_config, failure = load_yaml(filename)

# from pprint import pprint; pprint(local_config)
if failure:
    print(f"Failed with {failure}")
else:
    for k, v in local_config.items():
        environ[k] = v
        system(f"export {k}={v}")
        print(f'export {k}="{v}"')
    print(f'export LATIGO_LOCAL_CONF_FILENAME="{filename}"')

