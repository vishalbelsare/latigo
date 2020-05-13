from latigo.types import ModelTrainingPeriod, PredictionDataSet, Task


class PredictionExecutionProviderInterface:
    def execute_prediction(
        self, task: Task, revision: str, model_training_period: ModelTrainingPeriod,
    ) -> PredictionDataSet:
        """Train and/or run data through a given model."""
        raise NotImplementedError()


def prediction_execution_provider_factory(
    sensor_data_provider, prediction_storage_provider, prediction_execution_config
):
    prediction_execution_type = prediction_execution_config.get("type", None)
    if "gordo" == prediction_execution_type:
        from latigo.gordo import GordoPredictionExecutionProvider

        prediction_execution = GordoPredictionExecutionProvider(
            sensor_data_provider, prediction_storage_provider, prediction_execution_config,
        )
    else:
        raise ValueError(f"prediction_execution_type can not be {prediction_execution_type}")

    return prediction_execution
