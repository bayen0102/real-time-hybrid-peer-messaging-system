import json
import logging
import sys
from datetime import datetime, timezone

logger = logging.getLogger("messaging-service")
logger.setLevel(logging.INFO)

handler = logging.StreamHandler(sys.stdout)
logger.addHandler(handler)


def log_event(event, **data):
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **data
    }

    logger.info(json.dumps(log_data))