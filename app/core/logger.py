import logging
from app.core.paths import data_path


def setup_logger():
    log_file = data_path() / "log.txt"

    logger = logging.getLogger("CS2ConfigManager")
    logger.setLevel(logging.INFO)

    # Чтобы не дублировать хендлеры при перезапусках
    if not logger.handlers:
        handler = logging.FileHandler(log_file, encoding="utf-8")
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


log = setup_logger()