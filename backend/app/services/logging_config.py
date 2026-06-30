from __future__ import annotations

import logging
from datetime import datetime, timezone

from ..config import LOGS_DIR

logger = logging.getLogger(__name__)


def setup_logging(retention_days: int = 30) -> None:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOGS_DIR / "app.log"
    handlers: list[logging.Handler] = [
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
    prune_old_logs(retention_days)


def prune_old_logs(retention_days: int) -> None:
    if retention_days <= 0:
        return
    cutoff = datetime.now(timezone.utc).timestamp() - retention_days * 86400
    for path in LOGS_DIR.glob("app.log*"):
        if path.name == "app.log":
            continue
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Failed to prune log %s: %s", path, exc)
