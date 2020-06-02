import factory

from latigo.model_info import Model


class ModelFactory(factory.Factory):
    model_name = factory.Sequence(lambda n: f"model{n:05}")
    project_name = factory.Sequence(lambda n: f"project{n:05}")
    tag_list = []
    target_tag_list = []

    class Meta:
        model = Model
