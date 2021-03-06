import logging
from typing import List

from latigo.gordo.gordo_exceptions import NoTagDataInDataLake
from latigo.log import measure
from latigo.types import ModelTrainingPeriod, PredictionDataSetMetadata, Task

from .client_pool import PredictionExecutionProviderInterface, GordoClientPool, PredictionDataSet, TimeRange
from .misc import expand_gordo_connection_string, expand_gordo_data_provider, expand_gordo_prediction_forwarder

logger = logging.getLogger(__name__)


class GordoPredictionExecutionProvider(PredictionExecutionProviderInterface):
    def __init__(self, sensor_data_provider, prediction_storage_provider, config):
        self.config = config
        if not self.config:
            raise Exception("No predictor_config specified")
        expand_gordo_connection_string(self.config)
        expand_gordo_data_provider(self.config, sensor_data_provider=sensor_data_provider)
        expand_gordo_prediction_forwarder(self.config, prediction_storage_provider=prediction_storage_provider)
        self.gordo_pool = GordoClientPool(self.config)

    def __str__(self):
        return f"GordoPredictionExecutionProvider"

    @measure("execute_prediction")
    def execute_prediction(
        self, task: Task, revision: str, model_training_period: ModelTrainingPeriod,
    ) -> PredictionDataSet:
        project_name = task.project_name
        model_name = task.model_name
        from_time = task.from_time
        to_time = task.to_time

        meta_data = PredictionDataSetMetadata(
            project_name=project_name,
            model_name=model_name,
            revision=revision,
            model_training_period=model_training_period,
        )

        client = self.gordo_pool.allocate_instance(project_name)
        if not client:
            raise Exception(f"No gordo client found for project '{project_name}' in gordo.execute_prediction()")

        try:
            result = client.predict(start=from_time, end=to_time, targets=[model_name], revision=revision)
        except KeyError as e:
            if "not in index" in str(e):  # data error (not some code error): "['GRA-TE -23-0701.PV'] not in index"
                raise NoTagDataInDataLake(project_name, model_name, from_time, to_time, e)
            raise

        if not result:
            raise Exception("No result in gordo.execute_prediction()")
        prediction_errors: List[str] = result[0][2]
        if prediction_errors:
            raise Exception("Prediction failed in Gordo with: %s", '; '.join(prediction_errors))
        return PredictionDataSet(
            meta_data=meta_data, time_range=TimeRange(from_time=from_time, to_time=to_time), data=result
        )
