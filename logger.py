import json
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
import os

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

logger = logging.getLogger("inspection")
logger.setLevel(logging.INFO)
logger.propagate = False

# 避免模块被重复导入时重复绑定 handler，导致日志重复写入
if not logger.handlers:
    handler = TimedRotatingFileHandler(
        filename=f"{LOG_DIR}/inspection.log",
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )

    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)


def log_result(result):
    """写入 JSON 日志"""
    record = {
        "time": datetime.now().isoformat(),
        **result
    }
    logger.info(json.dumps(record, ensure_ascii=False))
