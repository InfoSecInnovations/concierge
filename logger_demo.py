# note the pythonjsonlogger can be installed via:
# pip install python-json-logger


import logging
import sys
import time
from pythonjsonlogger import jsonlogger
# from datetime import datetime


logger = logging.getLogger("jsonLogger")

# stdout for debug
log_handler = logging.StreamHandler(sys.stdout)

# for logging to file
# filename = "./log.json"
# logHandler = logging.FileHandler(filename, mode='a', encoding=None, delay=False, errors=None)

# UTC||GTFO
logging.Formatter.converter = time.gmtime

formatter = jsonlogger.JsonFormatter(
    fmt="%(asctime)s %(levelname)s %(message)s",
    json_ensure_ascii=False,
    rename_fields={"levelname": "severity", "asctime": "eventtime"},
)
log_handler.setFormatter(formatter)
logger.addHandler(log_handler)


def app():
    # hardcoding values for demo only
    user = "douglas"
    userid = 8472790
    collection = {
        "name": "testing",
        "id": 277578,
        "location": "private",
        "owner": 8472790,
    }

    logger.debug("Debugging message with internal details.")
    # logger.error("Failed to connect to database.", extra={"db_host": "db.prod.local"})
    logger.error("testing", extra={"collection_id": collection["id"]})
    logger.warning(
        "testing2",
        extra={"user": {"username": user, "id": userid}, "collection": collection},
    )

    1 / 0


if __name__ == "__main__":
    try:
        app()
    except Exception as e:
        logger.critical(e, exc_info=True)
        raise e
