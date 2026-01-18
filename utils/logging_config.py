import logging
from pathlib import Path


def setup_logging(*, log_level: str, log_file: str = "data/logs/app.log") -> None:
    log_dir = Path(log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    level = getattr(logging, log_level.upper(), logging.INFO)

    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8"),
        ],
    )

