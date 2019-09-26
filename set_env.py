#!/usr/bin/env python

from os import environ, path

from app.latigo.utils import load_yaml, save_yaml

filename='local_config.yaml'
local_config={}

if not path.exists(filename):
    # Create a starting point for local config so that user can get quickly up and running
    local_config['LATIGO_MESSAGE'] = f"YOUR LOCAL ENV CAN NOW BE EDITED IN {filename}. RE-RUN THIS SCRIPT TO LOAD ANY CHANGES"
    local_config['LATIGO_INTERNAL_EVENT_HUB'] = "GET YOUR EVENT_HUB CONNECTION STRING FROM AZURE PORTAL"
    save_yaml(filename, local_config)
else:
    local_config = load_yaml(filename)

for k, v in local_config.items():
    environ[k] = v
    print(f'export {k}="{v}"')

