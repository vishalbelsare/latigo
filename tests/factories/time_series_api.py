import factory.fuzzy

from latigo.types import LatigoSensorTag, SensorDataSpec


class LatigoSensorTagFactory(factory.Factory):
    name = factory.Sequence(lambda n: f"GRA-{n:05}")
    asset = factory.Sequence(lambda n: f"1313-{n:05}")

    class Meta:
        model = LatigoSensorTag


class SensorDataSpecFactory(factory.Factory):
    tag_list = factory.List([factory.SubFactory(LatigoSensorTagFactory) for _ in range(3)])

    class Meta:
        model = SensorDataSpec
