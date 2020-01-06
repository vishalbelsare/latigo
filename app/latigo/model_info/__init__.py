import logging
import typing
from latigo.types import SensorDataSpec, LatigoSensorTag

logger = logging.getLogger(__name__)


def model_key(project_name: str, model_name: str) -> str:
    return project_name + "-" + model_name


class Model:
    """
    Wrap model in 'neutral' class
    """

    def __init__(self, model_name: str, project_name: str, tag_list: typing.List[LatigoSensorTag], target_tag_list: typing.List[LatigoSensorTag]):
        self.model_name = model_name
        self.project_name = project_name
        self.tag_list = tag_list
        self.target_tag_list = target_tag_list

    def key(self):
        return model_key(self.project_name, self.model_name)

    def get_spec(self) -> typing.Optional[SensorDataSpec]:
        return SensorDataSpec(tag_list=self.tag_list)


class ModelInfoProviderInterface:
    def get_all_models(self, projects: typing.List):
        pass

    def get_model_by_key(self, project_name: str, model_name: str):
        pass

    def get_spec(self, project_name: str, model_name: str) -> typing.Optional[SensorDataSpec]:
        """
        Return a sensor data spec for given project name and model name
        """
        pass


class MockModelInfoProvider(ModelInfoProviderInterface):
    def __init__(self, config: dict):
        self.config = config

    def get_all_models(self, projects: typing.List):
        return []

    def get_model_by_key(self, project_name: str, model_name: str):
        return None

    def get_spec(self, project_name: str, model_name: str) -> typing.Optional[SensorDataSpec]:
        return None


class DevNullModelInfoProvider(ModelInfoProviderInterface):
    def __init__(self, config: dict):
        pass

    def get_all_models(self, projects: typing.List):
        return []

    def get_model_by_key(self, project_name: str, model_name: str):
        return None

    def get_spec(self, project_name: str, model_name: str) -> typing.Optional[SensorDataSpec]:
        return None


def model_info_provider_factory(model_info_provider_config):
    model_info_provider_type = model_info_provider_config.get("type", None)
    model_info_provider = None

    if "gordo" == model_info_provider_type:
        from latigo.gordo import GordoModelInfoProvider

        model_info_provider = GordoModelInfoProvider(config=model_info_provider_config)

    elif "mock" == model_info_provider_type:
        model_info_provider = MockModelInfoProvider(config=model_info_provider_config)
    else:
        model_info_provider = DevNullModelInfoProvider(config=model_info_provider_config)
    return model_info_provider
