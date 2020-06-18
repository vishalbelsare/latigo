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

    def __init__(
        self,
        model_name: str,
        project_name: str,
        tag_list: typing.List[LatigoSensorTag],
        target_tag_list: typing.List[LatigoSensorTag],
    ):
        self.model_name = model_name
        self.project_name = project_name
        self.tag_list = tag_list
        self.target_tag_list = target_tag_list

    def key(self):
        return model_key(self.project_name, self.model_name)

    def get_spec(self) -> typing.Optional[SensorDataSpec]:
        return SensorDataSpec(tag_list=self.tag_list)


class ModelInfoProviderInterface:
    def get_all_model_names_by_project(self, projects: typing.List):
        raise NotImplementedError()

    def get_model_by_key(self, project_name: str, model_name: str):
        raise NotImplementedError()

    def get_spec(self, project_name: str, model_name: str) -> typing.Optional[SensorDataSpec]:
        """
        Return a sensor data spec for given project name and model name
        """
        raise NotImplementedError()


def model_info_provider_factory(model_info_provider_config):
    model_info_provider_type = model_info_provider_config.get("type", None)

    if "gordo" == model_info_provider_type:
        from latigo.gordo import GordoModelInfoProvider

        model_info_provider = GordoModelInfoProvider(config=model_info_provider_config)
    else:
        raise ValueError(f"'{model_info_provider_type}' in not valid model info provider type")
    return model_info_provider
