from latigo.sensor_data import SensorData, TimeRange


class SensorDataProviderInterface:
    def get_data_for_range(self, time_range: TimeRange) -> SensorData:
        """
        return the actual data as per the range specified
        """
        pass


class MockSensorDataProvider(SensorDataProviderInterface):
    def get_data_for_range(self, time_range: TimeRange) -> SensorData:
        """
        return the actual data as per the range specified
        """
        data = SensorData(time_range)

        return data
