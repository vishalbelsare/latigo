import os
import sys
import logging

ENVIRONMENT = os.getenv('ENVIRONMENT', "LOCAL")


class Local:
    AAD_TENANT_ID: str = ""
    AAD_APPLICATION_ID: str = ""
    AAD_APPLICATION_SECRET: str = ""
    KUSTO_URI: str = ""
    KUSTO_INGEST_URI: str = ""
    KUSTO_DATABASE: str = ""
    SERVICE_BUSS_CONN_STR: str = ""
    GORDO_PROJECT: str = ""
    CONFIG_ITEMS_COMPULSORY = [
        "AAD_TENANT_ID",
        "AAD_APPLICATION_ID",
        "AAD_APPLICATION_SECRET",
        "SERVICE_BUSS_CONN_STR",
        "GORDO_PROJECT"]

    MODEL_UPDATE_TIME = 10  # Model update time in seconds
    DEBUG_LEVEL = logging.DEBUG

    QUEUE_NAME_GORDO_PREDICTION = f"{ENVIRONMENT}_gordo_prediction"
    QUEUE_NAME_GORDO_ADX_WRITES = f"{ENVIRONMENT}_gordo_adx_writes"

    def __init__(self, name):
        self.name = name
        self.errors = ''
        for config_item in self.CONFIG_ITEMS_COMPULSORY:
            config_value = os.getenv(config_item)
            if config_value:
                setattr(self, config_item, config_value)
            else:
                self.errors += f"Missing environment variable: {config_item}\n"

    def __str__(self):
        ret = f"Environment {self.name}\nPython version {sys.version}\n"
        if self.errors:
            ret += f"Errors:\n{self.errors}\n"
        return ret

    def exit_on_errors(self):
        if self.errors:
            print(f"Could not start, configuration had errors: {self.errors}")
            sys.exit(1)


class Dev(Local):
    pass


class Staging(Local):
    pass


class Prod(Local):
    pass


class UnitTest(Local):
    def __init__(self):
        pass


if ENVIRONMENT == "PROD":
    CONFIG = Prod(ENVIRONMENT)
elif ENVIRONMENT == "STAGING":
    CONFIG = Staging(ENVIRONMENT)
elif ENVIRONMENT == "DEV":
    CONFIG = Dev(ENVIRONMENT)
elif ENVIRONMENT == "TEST":
    CONFIG = UnitTest(ENVIRONMENT)
else:
    CONFIG = Local('LOCAL')
