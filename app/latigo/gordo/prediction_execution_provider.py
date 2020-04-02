from latigo.gordo.gordo_exceptions import NoTagDataInDataLake
from latigo.types import ModelTrainingPeriod, PredictionDataSetMetadata

from .client_pool import *
from .misc import *

logger = logging.getLogger(__name__)


class GordoPredictionExecutionProvider(PredictionExecutionProviderInterface):
    def _prepare_projects(self):
        self.projects = self.config.get("projects", [])
        if not isinstance(self.projects, list):
            self.projects = [self.projects]

    def __init__(self, sensor_data_provider, prediction_storage_provider, config):
        self.config = config
        if not self.config:
            raise Exception("No predictor_config specified")
        expand_gordo_connection_string(self.config)
        expand_gordo_data_provider(self.config, sensor_data_provider=sensor_data_provider)
        expand_gordo_prediction_forwarder(self.config, prediction_storage_provider=prediction_storage_provider)
        self.gordo_pool = GordoClientPool(self.config)
        self._prepare_projects()

    def __str__(self):
        return f"GordoPredictionExecutionProvider({self.projects})"

    def execute_prediction(
        self,
        project_name: str,
        model_name: str,
        sensor_data: SensorDataSet,
        revision: str,
        model_training_period: ModelTrainingPeriod,
    ) -> PredictionDataSet:
        if not project_name:
            raise Exception("No project_name in gordo.execute_prediction()")
        if not model_name:
            raise Exception("No model_name in gordo.execute_prediction()")
        if not sensor_data:
            raise Exception("No sensor_data in gordo.execute_prediction()")

        meta_data = PredictionDataSetMetadata(
            project_name=project_name,
            model_name=model_name,
            revision=revision,
            model_training_period=model_training_period,
        )

        if not sensor_data.data:
            logger.warning(f"No data in prediction for project '{project_name}' and model {model_name}")
            return PredictionDataSet(time_range=sensor_data.time_range, data=None, meta_data=meta_data)
        if len(sensor_data.data) < 1:
            logger.warning(f"Length of data < 1 in prediction for project '{project_name}' and model {model_name}")
            return PredictionDataSet(time_range=sensor_data.time_range, data=None, meta_data=meta_data)
        client = self.gordo_pool.allocate_instance(project_name)
        if not client:
            raise Exception(f"No gordo client found for project '{project_name}' in gordo.execute_prediction()")
        print_client_debug(client)
        try:
            result = client.predict(
                start=sensor_data.time_range.from_time,
                end=sensor_data.time_range.to_time,
                targets=[model_name],
                revision=revision,
            )
        except KeyError as e:
            raise NoTagDataInDataLake(
                project_name, model_name, sensor_data.time_range.from_time, sensor_data.time_range.to_time, e
            )

        if not result:
            raise Exception("No result in gordo.execute_prediction()")
        return PredictionDataSet(meta_data=meta_data, time_range=sensor_data.time_range, data=result)
