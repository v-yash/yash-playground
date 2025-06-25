import logging
from typing import Optional

class Logger:
    @staticmethod
    def get_logger(format: str = "text") -> logging.Logger:
        """Configure and return a logger instance."""
        logger = logging.getLogger("k8s_resource_analyzer")
        logger.setLevel(logging.INFO)
        
        # Clear existing handlers to avoid duplicate logs
        if logger.handlers:
            logger.handlers.clear()
        
        if format == "json":
            formatter = logging.Formatter(
                '{"time": "%(asctime)s", "origin": "p%(process)s %(filename)s:%(name)s:%(lineno)d", '
                '"log_level": "%(levelname)s", "log": "%(message)s"}'
            )
        else:
            formatter = logging.Formatter(
                "[%(levelname)s] %(asctime)s p%(process)s %(filename)s:%(name)s:%(lineno)d %(message)s"
            )
        
        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger  # This line was missing!