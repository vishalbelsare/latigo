from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class Task:
    name: str
    from_time: datetime = datetime.now() - + timedelta(0, 20)
    to_time: datetime = datetime.now()


@dataclass
class TimeRange:

    from_time: datetime
    to_time: datetime


@dataclass
class SensorData:

    def __str__(self):
        return "PredictionData"


@dataclass
class PredictionData:

    def __str__(self):
        return "PredictionData"
