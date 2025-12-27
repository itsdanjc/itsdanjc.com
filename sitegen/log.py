from enum import Enum
import logging

logger = logging.getLogger(__name__)

class LogColors(Enum):
    WARNING = '\033[33m'
    ERROR = '\033[31m'
    RESET = '\033[0m'

class LogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord):
        message = record.getMessage()
        warn_format = f"{LogColors.WARNING.value}Warn: {message}{LogColors.RESET.value}"
        error_format = f"{LogColors.ERROR.value}Error: {message}{LogColors.RESET.value}"

        if record.levelno == logging.WARNING:
            return warn_format

        elif record.levelno == logging.ERROR:
            return error_format

        return message


def configure_logging(verbose: bool):
    handler = logging.StreamHandler()
    handler.setFormatter(LogFormatter())

    logging.basicConfig(
        level=(logging.DEBUG if verbose else logging.INFO),
        handlers=[handler]
    )