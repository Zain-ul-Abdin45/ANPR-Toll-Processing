import logging
import os
import configparser
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

def load_config(path="configs/logger.ini"):
    config = configparser.ConfigParser()
    config.read(path)
    if "LOGGING" not in config:
        raise KeyError("LOGGING section not found in logger.ini!")
    return config["LOGGING"]


def setup_rotating_logger(name, log_dir, prefix, level=logging.INFO, when='midnight', backup_count=7):
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, f"{prefix}.log")

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # logs loop handler again

    # REMOVE existing handlers to avoid duplicates during reload
    if logger.hasHandlers():
        logger.handlers.clear()

    handler = TimedRotatingFileHandler(
        log_file_path,
        when=when,
        interval=1,
        backupCount=backup_count,
        encoding='utf-8',
        utc=False
    )
    handler.suffix = "%d_%m_%Y"
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


# Load configuration
log_config = load_config()
log_level = getattr(logging, log_config.get("log_level", "INFO"))

# Setup each logger
plate_logger = setup_rotating_logger(
    "plate_logger",
    log_config["plate_log_dir"],
    log_config["plate_log_prefix"],
    log_level
)

rfid_logger = setup_rotating_logger(
    "rfid_logger",
    log_config["rfid_log_dir"],
    log_config["rfid_log_prefix"],
    log_level
)

txn_logger = setup_rotating_logger(
    "txn_logger",
    log_config["transaction_log_dir"],
    log_config["transaction_log_prefix"],
    log_level
)

alert_logger = setup_rotating_logger(
    "alert_logger",
    log_config["alert_log_dir"],
    log_config["alert_log_prefix"],
    log_level
)

general_logger = setup_rotating_logger(
    "general_logger",
    log_config["general_log_dir"],
    log_config["general_log_prefix"],
    log_level
)


log_config = load_config()


if __name__ == "__main__":
    plate_logger.info("Test log: plate_logger works")
    rfid_logger.info("Test log: rfid_logger works")
    txn_logger.info("Test log: txn_logger works")
    alert_logger.info("Test log: alert_logger works")
    general_logger.info("Test log: general_logger works")
