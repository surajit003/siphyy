"""Siphyy — open-source agentic framework for fleet telematics analytics."""

__version__ = "0.1.0"

from siphyy.schema import CanonicalEvent, DriverEvent, TelemetryReading

__all__ = ["CanonicalEvent", "DriverEvent", "TelemetryReading", "__version__"]
