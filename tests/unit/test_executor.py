import logging

from latigo.executor import PredictionExecutor

logger = logging.getLogger(__name__)


def test_fetch_task(config):
    pe = PredictionExecutor(config=config)

    ret = pe.fetch_spec(project_name="project", model_name="model")
    logger.info(ret)
