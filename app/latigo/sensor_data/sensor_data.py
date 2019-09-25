from datetime import datetime



class SensorDataProviderInterface:

    def get_native_range_specifier(self, from_time:datetime, to_time:datetime, parameters:str) -> RangeSpecifier:
        """
        return a specification of the given time span in native representation. For example for influx this would be an influx query or complete query url (parameter can be used to select)
        """
        pass

    def get_data_for_range(self, time_range: RangeSpecifier) -> SensorData:
        """
        return the actual data as per the range specified
        """
        pass


class MockSensorDataProvider(SensorDataProviderInterface):

    def get_native_range_specifier(self, from_time:datetime, to_time:datetime, parameters:str) -> RangeSpecifier:
        """
        return a specification of the given time span in native representation. For example for influx this would be an influx query or complete query url (parameter can be used to select)
        """
        rs=RangeSpecifier()
        rs.from_time=from_time
        rs.to_time=to_time
        return rs

    def get_data_for_range(self, time_range: RangeSpecifier) -> SensorData:
        """
        return the actual data as per the range specified
        """
        data=SensorData()

        return data
