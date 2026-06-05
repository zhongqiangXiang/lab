"""Logging configuration."""

import logging
import sys


def setup_logging(verbose: bool = False) -> None:
    """
    Setup logging configuration.

    Args:
        verbose: Enable debug logging if True
    """
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )

    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)
