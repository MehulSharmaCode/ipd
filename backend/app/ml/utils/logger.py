import logging


def get_logger(name: str):

    logger = logging.getLogger(name)

    if not logger.handlers:
        logger.setLevel(logging.INFO)

        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        handler = logging.StreamHandler()
        handler.setFormatter(formatter)

        logger.addHandler(handler)

    return logger