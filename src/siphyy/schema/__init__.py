"""Canonical event schema — the framework contract.

Everything past the adapter layer reasons in these types only.
Provider-specific shapes never leak past the adapter.
"""

from siphyy.schema.canonical import (
    BaseEvent,
    CanonicalEvent,
    DriverEvent,
    DriverEventSubtype,
    EngineState,
    TelemetryReading,
)
from siphyy.schema.case import (
    CaseBase,
    CaseCategory,
    IncidentCase,
    Severity,
)

__all__ = [
    "BaseEvent",
    "CanonicalEvent",
    "CaseBase",
    "CaseCategory",
    "DriverEvent",
    "DriverEventSubtype",
    "EngineState",
    "IncidentCase",
    "Severity",
    "TelemetryReading",
]
