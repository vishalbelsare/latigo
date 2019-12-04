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


class ModelInfo:
    def __init__(self):
        self.models_by_key = {}
        self.models_list = []

    def register_model(self, model: Model):
        key = model.key()
        self.models_by_key[key] = model
        self.models_list.append(model)

    def get_all(self):
        return self.models_list

    def get_model_by_key(self, key: str):
        return self.models_by_key.get(key, None)

    def get_spec(self, project_name: str, model_name: str) -> typing.Optional[SensorDataSpec]:
        """
        Return a sensor data spec for given project name and model name
        """
        key = model_key(project_name, model_name)
        model = self.get_model_by_key(key)
        if not model:
            return None
        return model.get_spec()


class ModelInfoProviderInterface:
    def get_model_info(self) -> ModelInfo:
        """
        Return the model info
        """
        pass


class MockModelInfoProvider(ModelInfoProviderInterface):
    def __init__(self, config: dict):
        self.config = config

    def get_model_info(self) -> ModelInfo:
        return ModelInfo()


class DevNullModelInfoProvider(ModelInfoProviderInterface):
    def __init__(self, config: dict):
        pass

    def get_model_info(self) -> ModelInfo:
        return ModelInfo()


def model_info_provider_factory(model_info_provider_config):
    model_info_provider_type = model_info_provider_config.get("type", None)
    model_info_provider = None

    if "gordo" == model_info_provider_type:
        from latigo.gordo import GordoModelInfoProvider

        model_info_provider = GordoModelInfoProvider(model_info_provider_config)

    elif "mock" == model_info_provider_type:
        model_info_provider = MockModelInfoProvider(model_info_provider_config)
    else:
        model_info_provider = DevNullModelInfoProvider(model_info_provider_config)
    return model_info_provider
