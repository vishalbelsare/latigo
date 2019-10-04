import logging
import inspect

once = False


def setup_logging(filename, log_level=logging.INFO):
    global once
    if not once:
        once = True
        """Set up the logging."""
        logging.basicConfig(level=log_level)
        fmt = ("%(asctime)s %(levelname)s (%(threadName)s) "
               "[%(name)s] %(message)s")
        colorfmt = "%(log_color)s{}%(reset)s".format(fmt)
        datefmt = '%Y-%m-%d %H:%M:%S'

        # Suppress overly verbose logs from libraries that aren't helpful
        for key in [
            'requests',
            'tensorboard',
            'urllib3',
            'aiohttp.access',
            'uamqp',
            'sqlalchemy',
                'sqlalchemy.engine.base']:
            logging.getLogger(key).setLevel(logging.WARNING)

        try:
            from colorlog import ColoredFormatter
            logging.getLogger().handlers[0].setFormatter(ColoredFormatter(
                colorfmt,
                datefmt=datefmt,
                reset=True,
                log_colors={
                    'DEBUG': 'cyan',
                    'INFO': 'green',
                    'WARNING': 'yellow',
                    'ERROR': 'red',
                    'CRITICAL': 'red',
                }
            ))
        except ImportError:
            pass

        logger = logging.getLogger('')
        logger.setLevel(log_level)

    log_filename = inspect.stack()[1][1]
    logger = logging.getLogger(log_filename)
    logger.info(f"Log started for {log_filename}")
    return logger
