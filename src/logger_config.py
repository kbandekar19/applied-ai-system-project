import logging
import os
from datetime import datetime


def setup_logger(name: str = "vibematcher") -> logging.Logger:
    os.makedirs("logs", exist_ok=True)
    log_file = os.path.join("logs", f"vibematcher_{datetime.now().strftime('%Y%m%d')}.log")

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"))

    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger
