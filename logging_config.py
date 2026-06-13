#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared logging initialization.

Both the crawler entrypoint and the FastAPI entrypoint use this module so
application logs are written to the same rotating file as soon as either starts.
"""

import logging
import os
from logging.handlers import TimedRotatingFileHandler

from config import LOG_FILE

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
_FILE_HANDLER_MARKER = "_github_trending_spider_file_handler"
_STREAM_HANDLER_MARKER = "_github_trending_spider_stream_handler"


def setup_logging():
    """Initialize root logging once for application modules."""
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    formatter = logging.Formatter(_LOG_FORMAT)
    log_dir = os.path.dirname(LOG_FILE)
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    if not _has_handler(root_logger, _FILE_HANDLER_MARKER):
        file_handler = TimedRotatingFileHandler(
            LOG_FILE,
            when="midnight",
            interval=1,
            backupCount=30,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        setattr(file_handler, _FILE_HANDLER_MARKER, True)
        root_logger.addHandler(file_handler)

    if not _has_handler(root_logger, _STREAM_HANDLER_MARKER):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        setattr(stream_handler, _STREAM_HANDLER_MARKER, True)
        root_logger.addHandler(stream_handler)


def _has_handler(logger, marker):
    return any(getattr(handler, marker, False) for handler in logger.handlers)
