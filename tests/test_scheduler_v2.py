# -*- coding: utf-8 -*-
"""Tests for scheduler_v2."""

from datetime import timedelta

from app_config import parse_interval


def test_parse_interval():
    assert parse_interval("1h") == timedelta(hours=1)
    assert parse_interval("1d") == timedelta(days=1)
