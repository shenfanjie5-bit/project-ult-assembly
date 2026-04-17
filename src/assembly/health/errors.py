"""Errors raised by assembly healthcheck workflows."""

from __future__ import annotations


class HealthcheckError(Exception):
    """Base exception for healthcheck loading or execution failures."""

