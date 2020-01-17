from typing import List
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SensorInformation:
    """
    Class for keeping information about a sensor
    """

    sensor_name: str
    # TODO: what other information is available/useful?


@dataclass
class SensorDataPoint:
    """
    Class for keeping one individual sensor data point
    """

    pass


@dataclass
class SensorData:
    """
    Class for keeping sensor data
    """

    data: List[SensorDataPoint]


class SensorInformationProviderInterface:
    """
    Where can we get information about available sensors and their naming conventions?
    """

    def get_all_sensor(self) -> List[SensorInformation]:
        """Enumerate all available sensors"""
        pass

    def get_sensor_by_name(self, sensor_name: str) -> Optional[SensorInformation]:
        """Return information about one sensor ideintified by name"""
        pass

    def sensor_exists(self, sensor_name: str):
        """check if a sensor exists"""
        pass


class TestSensorInformationProvider(SensorInformationProviderInterface):
    """
    Test implementation of SensorInformationProviderInterface
    """

    sensor_information = [
        SensorInformation("SENSOR_A"),
        SensorInformation("SENSOR_B"),
        SensorInformation("SENSOR_C"),
    ]

    def get_all_sensor(self) -> List[SensorInformation]:
        """Enumerate all available sensors"""
        return self.sensor_information

    def get_sensor_by_name(self, sensor_name: str) -> Optional[SensorInformation]:
        """Return information about one sensor ideintified by name"""
        for sensor in self.sensor_information:
            if sensor_name == sensor.sensor_name:
                return sensor
        return None

    def sensor_exists(self, sensor_name: str):
        """check if a sensor exists"""
        for sensor in self.sensor_information:
            if sensor_name == sensor.sensor_name:
                return True
        return False
