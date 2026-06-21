# -*- coding: utf-8 -*-
"""Tests for scheduler_v2."""

from datetime import timedelta


def test_parse_interval():
    from scheduler_v2 import parse_interval
    assert parse_interval("1h") == timedelta(hours=1)
    assert parse_interval("1d") == timedelta(days=1)
