from typing import List, Dict


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

    def get_all_sensor() -> List[SensorInformation]:
        '''Enumerate all available sensors'''
        pass

    def get_sensor_by_name(sensor_name:str) -> SensorInformation:
        '''Return information about one sensor ideintified by name'''
        pass

    def sensor_exists(sensor_name:str):
        '''check if a sensor exists'''
        pass

class SensorDataProviderInterface:
    """
    Where can we get access to data from a sensor given its name?
    """

    def get_native_range_specifier(range_from:timestamp, range_to:timestamp, parameters:str):
        '''
        return a specification of the given time span in a representation that is native to
        this particular sensor data provider.
        For example for influx this would be an influx query or complete query url (parameter can be used to select)
        '''
        pass

    def get_data_for_range(sensor_name: str, range_from:timestamp, range_to:timestamp) -> SensorData:
        '''
        Return a dataset for the given sensor and timespan
        '''
        pass



class TestSensorInformationProvider(SensorInformationProviderInterface):
    """
    Test implementation of SensorInformationProviderInterface
    """
    sensor_information=[
        SensorInformation('SENSOR_A'),
        SensorInformation('SENSOR_B'),
        SensorInformation('SENSOR_C'),
    ]

    def get_all_sensor() -> List[SensorInformation]:
        '''Enumerate all available sensors'''
        return sensor_information

    def get_sensor_by_name(sensor_name:str) -> SensorInformation:
        '''Return information about one sensor ideintified by name'''
        for sensor in sensor_information:
            if sensor_name == sensor.sensor_name:
                return sensor
        return None

    def sensor_exists(sensor_name:str):
        '''check if a sensor exists'''
        for sensor in sensor_information:
            if sensor_name == sensor.sensor_name:
                return True
        return False



