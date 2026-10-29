"""日志：控制台 + `<DATA_DIR>/runs/doc.log`。api_key 一律打码（architecture.md 第 7 节）。"""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler

from documentary.core.config import Settings

_SECRET = re.compile(r"\b(api_key|apikey|access_token|token)=([^&\s]+)", re.IGNORECASE)


def redact(text: str) -> str:
    return _SECRET.sub(r"\1=***", text)


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact(record.getMessage())
        record.args = None
        return True


def setup_logging(settings: Settings) -> None:
    root = logging.getLogger("documentary")
    if root.handlers:
        return
    root.setLevel(settings.log_level)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")

    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    handlers: list[logging.Handler] = [console]

    log_dir = settings.data_dir / "runs"
    if settings.data_dir.exists():
        log_dir.mkdir(exist_ok=True)
        handlers.append(
            RotatingFileHandler(
                log_dir / "doc.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"
            )
        )
    for h in handlers:
        h.setFormatter(fmt)
        h.addFilter(RedactFilter())
        root.addHandler(h)
