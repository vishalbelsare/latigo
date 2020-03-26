"""Exceptions for the Gordo logic."""


class NoTagDataInDataLake(Exception):
    """Raise if there's no data in the Data Lake for particular tag for given period of time."""

    def __init__(self, project_name, model_name, from_time, to_time, e):
        self.message = f"Prediction was skipped. Reason: no data was found in the Data Lake for " \
                       f"project='{project_name}' :: model='{model_name}' :: " \
                       f"from='{from_time}' :: to='{to_time}' :: error='{e}'"
        super().__init__(self.message)
