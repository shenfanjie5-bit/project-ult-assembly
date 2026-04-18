"""Errors raised by the contract compatibility suite."""

from __future__ import annotations


class CompatibilityError(Exception):
    """Base exception for contract compatibility failures."""


class CompatibilityPromotionError(CompatibilityError):
    """Raised when a compatibility matrix entry cannot be promoted."""
