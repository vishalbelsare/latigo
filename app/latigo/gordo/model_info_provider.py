import logging
import typing

from latigo.types import ModelTrainingPeriod
from .client_pool import ModelInfoProviderInterface, GordoClientPool, Machine, Model, SensorDataSpec
from .data_provider import _gordo_to_latigo_tag_list
from .misc import expand_gordo_connection_string, expand_gordo_data_provider, expand_gordo_prediction_forwarder

logger = logging.getLogger(__name__)


class GordoModelInfoProvider(ModelInfoProviderInterface):
    def _prepare_auth(self):
        self.auth_config = self.config.get("auth")

    def __init__(self, config):
        self.config = config
        if not self.config:
            raise Exception("No machine_info_config specified")
        self._prepare_auth()
        expand_gordo_connection_string(self.config)
        expand_gordo_data_provider(config=self.config, sensor_data_provider=None)
        expand_gordo_prediction_forwarder(
            config=self.config, prediction_storage_provider=None
        )
        self.gordo_pool = GordoClientPool(raw_config=self.config)

    def __str__(self):
        return f"GordoModelInfoProvider()"

    def get_model_data(
        self, projects: typing.List[str], model_names: typing.Optional[typing.List] = None,
    ) -> typing.List[Machine]:
        machines: typing.List[Machine] = []
        if not projects:
            raise ValueError("'projects' can not be empty.")
        for project_name in projects:
            client = self.gordo_pool.allocate_instance(project_name)
            if client:
                try:
                    machines += client._get_machines(machine_names=model_names)
                except TypeError as e:
                    if "byte indices must be integers or slices, not str" not in str(e):
                        raise

                    # this is case when "project_name" is invalid.
                    # we will skip such project cause API might be not in sync with Gordo.
                    logger.exception("Invalid project: %s", project_name)
                    self.gordo_pool.delete_instance(project_name)  # delete invalid client from poll

            else:
                logger.error(f"No client found for project '{project_name}', skipping")

        if not machines:
            raise ValueError(f"No models/machines were found for projects: {' ;'.join(projects)}.")
        return machines

    def get_all_models(self, projects: typing.List) -> typing.List[Model]:
        machines = self.get_model_data(projects)
        models = []
        for machine in machines:
            if machine:
                project_name = machine.project_name or "unnamed"
                model_name = machine.name or "unnamed"
                model = Model(
                    project_name=project_name,
                    model_name=model_name,
                    tag_list=machine.dataset.tag_list,
                    target_tag_list=machine.dataset.target_tag_list,
                )
                if model:
                    models.append(model)

        if models:
            logger.info("Found %s models", len(models))
        else:
            logger.warning("No models found")

        return models

    def get_machine_by_key(
        self, project_name: str, model_name: str
    ) -> typing.Optional[Model]:
        machines = self.get_model_data(
            projects=[project_name], model_names=[model_name]
        )
        if not machines:
            return None
        model = None
        machine = machines[0]
        if machine:
            project_name = machine.project_name or "unnamed"
            model_name = machine.name or "unnamed"
            model = Model(
                project_name=project_name,
                model_name=model_name,
                tag_list=machine.dataset.tag_list,
                target_tag_list=machine.dataset.target_tag_list,
            )
        return model

    def get_spec(
        self, project_name: str, model_name: str
    ) -> typing.Optional[SensorDataSpec]:
        model = self.get_machine_by_key(
            project_name=project_name, model_name=model_name
        )
        if not model:
            return None
        spec = SensorDataSpec(tag_list=_gordo_to_latigo_tag_list(model.tag_list))
        return spec

    def get_project_latest_revisions(self, project_name: str):
        """Fetch latest revision(version) of the project in Gordo."""
        client = self.gordo_pool.allocate_instance(project_name)
        return client.get_revisions()["latest"]

    def get_model_training_dates(self, project_name: str, model_name: str, revision: str = None) -> ModelTrainingPeriod:
        """Fetch model training dates from Gordo."""
        client = self.gordo_pool.allocate_instance(project_name)
        machines = client._get_machines(revision=revision, machine_names=[model_name])

        train_end_date = machines[0].dataset.train_end_date
        train_start_date = machines[0].dataset.train_start_date

        return ModelTrainingPeriod(train_start_date=train_start_date, train_end_date=train_end_date)
