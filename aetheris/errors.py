"""Exception hierarchy for AETHERIS."""

from __future__ import annotations


class AetherisError(Exception):
    """Base class for all AETHERIS errors."""


class ConfigError(AetherisError):
    """Invalid configuration."""


class BusError(AetherisError):
    """Event-bus transport failure."""


class DetectorError(AetherisError):
    """Vision detector failure."""


class PolicyViolation(AetherisError):
    """A privacy/compliance policy blocked an action."""


class ServiceUnavailable(AetherisError):
    """A downstream service could not be reached."""
