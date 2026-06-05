import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configura logging estructurado con timestamp, level y nombre del logger."""
    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%dT%H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        datefmt=datefmt,
        stream=sys.stdout,
        force=True,
    )

    # Silenciar loggers ruidosos de librerías externas
    for noisy in ("httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
