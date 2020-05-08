import logging
import inspect

from opencensus.ext.azure.log_exporter import AzureLogHandler


once = False


def setup_logging(filename, log_level=logging.INFO):
    """Set up the logging."""
    global once
    if not once:
        once = True
        logging.basicConfig(level=log_level)
        fmt = "%(asctime)s %(levelname)s (%(threadName)s) " "[%(name)s] %(message)s"
        colorfmt = "%(log_color)s{}%(reset)s".format(fmt)
        datefmt = "%Y-%m-%d %H:%M:%S"

        # Suppress overly verbose output that isn't helpful from some libraries we depend on
        for key in [
            "requests",
            "tensorboard",
            "urllib3",
            "aiohttp.access",
            "uamqp",
            "adal-python",
            "matplotlib.font_manager",
            "gordo",
        ]:
            logging.getLogger(key).setLevel(logging.WARNING)

        logging.getLogger("gordo.client").setLevel(logging.DEBUG)
        try:
            from colorlog import ColoredFormatter

            logging.getLogger().handlers[0].setFormatter(
                ColoredFormatter(
                    colorfmt,
                    datefmt=datefmt,
                    reset=True,
                    log_colors={
                        "DEBUG": "cyan",
                        "INFO": "green",
                        "WARNING": "yellow",
                        "ERROR": "red",
                        "CRITICAL": "red",
                    },
                )
            )
        except ImportError:
            pass

        logger = logging.getLogger("")
        logger.setLevel(log_level)

    log_filename = inspect.stack()[1][1]
    logger = logging.getLogger(log_filename)
    logger.info(f"Log started for {log_filename}")
    return logger

def add_azure_logging(logger, enable_azure_logging=False, azure_monitor_instrumentation_key=None):
    if enable_azure_logging:
        if not azure_monitor_instrumentation_key:
            raise ValueError("'azure_monitor_instrumentation_key' can not be empty if Azure logging is enabled")

            logger.addHandler(AzureLogHandler(connection_string='InstrumentationKey=' + azure_monitor_instrumentation_key))
            logger.info("AzureLogHandler was enabled.")
