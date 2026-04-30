"""
Vectoria Logger — Structured, reusable logging for all modules.

Provides a single ``get_logger`` factory that returns a named logger with:
    - **Console handler** — coloured, human-readable output at INFO level.
    - **Rotating file handler** — detailed DEBUG output written to
      ``logs/vectoria.log`` with automatic rotation (5 MB × 3 backups).

Log format
----------
``[2026-04-30 17:00:00] [INFO ] [ingestion.loader] Loaded 42 documents | time_ms=312``

The structured ``key=value`` suffix is a convention — callers include it
in the message string.  This keeps the stdlib logger without pulling in
structlog while remaining grep-friendly and parseable.

Usage
-----
::

    from vectoria.logger import get_logger

    logger = get_logger(__name__)
    logger.info("Loaded documents | count=%d time_ms=%d", count, elapsed)

Design decisions
----------------
- stdlib ``logging`` only — zero extra dependencies.
- ``get_logger`` is idempotent: calling it twice with the same name
  returns the same logger, no duplicate handlers.
- File handler is created lazily (LOG_DIR is mkdir'd on first call).
- Console uses a short format; file uses a long format with filename/lineno.
"""

from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

from vectoria.config import LOG_DIR, LOG_LEVEL, LOG_FILE_LEVEL, LOG_MAX_BYTES, LOG_BACKUP_COUNT

# ─────────────────────────────────────────────────────────────────────
# Format strings
# ─────────────────────────────────────────────────────────────────────

_CONSOLE_FMT = "[%(asctime)s] [%(levelname)-5s] [%(name)s] %(message)s"
_FILE_FMT = (
    "[%(asctime)s] [%(levelname)-5s] [%(name)s] "
    "%(message)s  (%(filename)s:%(lineno)d)"
)
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

# ─────────────────────────────────────────────────────────────────────
# Internal state
# ─────────────────────────────────────────────────────────────────────

_initialised: bool = False
_file_handler: Optional[RotatingFileHandler] = None


def _ensure_initialised() -> None:
    """One-time setup: create log directory and shared file handler."""
    global _initialised, _file_handler  # noqa: PLW0603

    if _initialised:
        return

    # Create log directory if it doesn't exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOG_DIR / "vectoria.log"
    _file_handler = RotatingFileHandler(
        filename=str(log_file),
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    _file_handler.setLevel(getattr(logging, LOG_FILE_LEVEL.upper(), logging.DEBUG))
    _file_handler.setFormatter(logging.Formatter(_FILE_FMT, datefmt=_DATE_FMT))

    _initialised = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger configured with console and file handlers.

    Args:
        name: Logger name — typically ``__name__`` of the calling module.
              Example: ``"vectoria.ingestion.loader"``

    Returns:
        A :class:`logging.Logger` instance.  Calling this function
        multiple times with the same *name* returns the same logger
        (no duplicate handlers).
    """
    _ensure_initialised()

    logger = logging.getLogger(name)

    # Avoid adding handlers if they already exist (idempotent)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)  # let handlers filter

    # ── Console handler ──────────────────────────────────────────
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    console.setFormatter(logging.Formatter(_CONSOLE_FMT, datefmt=_DATE_FMT))
    logger.addHandler(console)

    # ── File handler (shared instance) ───────────────────────────
    if _file_handler is not None:
        logger.addHandler(_file_handler)

    # Prevent propagation to the root logger (avoids duplicate output)
    logger.propagate = False

    return logger
