#!/usr/bin/env python

from os import environ, path, system

from latigo.utils import load_yaml, save_yaml

pwd=path.dirname(path.realpath(__file__))

filename = pwd+"/local_config.yaml"

local_config = {}
failure = None

if not path.exists(filename):
    # Create a starting point for local config so that user can get quickly up
    # and running
    # fmt: off
    local_config={
        "LATIGO_EXECUTOR_CONFIG_FILE": "THE LOCATION OF PREDICTION EXECUTOR CONFIG FILE IN YAML FORMAT",
        "LATIGO_SCHEDULER_CONFIG_FILE": "THE LOCATION OF PREDICTION SCHEDULER CONFIG FILE IN YAML FORMAT",
        "DOCKER_REGISTRY": "The hostname of docker registry",
        "DOCKER_REPO": "The name of the repository in docker registry",
        "DOCKER_USERNAME": "The username for docker registry",
        "DOCKER_PASSWORD": "The password for docker registry"
    }
    # fmt: on
    
    save_yaml(filename, local_config)
else:
    local_config, failure = load_yaml(filename)

# from pprint import pprint; pprint(local_config)
if failure:
    print(f"false # Failed with {failure}")
else:
    for k, v in local_config.items():
        environ[k] = str(v)
        print(f'export {k}="{v}"')
    print(f'export LATIGO_LOCAL_CONF_FILENAME="{filename}"')

