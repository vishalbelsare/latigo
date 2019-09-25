import os.path
from deployer import *
import pprint
import threading
import time
import re
import sys
import logging
import datetime
import os

from azure.eventhub import EventHubClient, Sender, EventData, Offset



def deploy_stuff():
    my_subscription_id = os.environ.get('AZURE_SUBSCRIPTION_ID', '11111111-1111-1111-1111-111111111111')   # your Azure Subscription Id
    my_resource_group = os.environ.get('AZURE_RESOURCE_GROUP', 'undefined')
    my_pub_ssh_key_path = os.path.expanduser('~/.ssh/id_rsa.pub')   # the path to your rsa public key file


    print(f"\nInitializing the Deployer class with subscription id: {my_subscription_id}, resource group: {my_resource_group}" \
    "\nand public key located at: {my_pub_ssh_key_path}...\n\n")

    parameters={
    "namespaces_lroll_gordo_client_ioc_name":"arne"
    }

    # Initialize the deployer class
    deployer = Deployer(my_subscription_id, my_resource_group, my_pub_ssh_key_path)

    print("Beginning the deployment... \n\n")
    # Deploy the template
    my_deployment = deployer.deploy()

    print("Done deploying!!\n\nYou can connect via: `ssh azureSample@{}.westus.cloudapp.azure.com`".format(deployer.dns_label_prefix))

    # Destroy the resource group which contains the deployment
    # deployer.destroy()
