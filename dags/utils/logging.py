import logging

from loguru import logger


class _PropagateHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        logging.getLogger(record.name).handle(record)


def configure_loguru() -> None:
    logger.remove()
    logger.add(_PropagateHandler(), format="{message}", level="DEBUG")
