"""Seed cases for the Knowledge Pack v0.1.

These are realistic synthetic cases modeled on patterns common in African
and other emerging-market fleet operations. They serve as:
  1. A starter set for new deployments before real cases accumulate.
  2. Examples of the prose register cases should be written in.
  3. Test fixtures for the retrieval and agent layers.

Real customer-derived cases live in the proprietary Siphyy Knowledge Pack,
not in this open-source repo.
"""

from __future__ import annotations

from datetime import datetime

from siphyy.schema import IncidentCase

SEED_CASES: list[IncidentCase] = [
    IncidentCase(
        case_id="fuel_theft_0001",
        category="fuel_theft",
        severity="high",
        region="Zambia",
        vehicle_type="beverage truck",
        summary=(
            "Fuel level dropped 47% over 18 minutes while engine_state was stopped "
            "and ignition was off. Location was an unlit industrial road at 02:14 "
            "local time, 8km off the planned route. Vehicle had completed delivery "
            "5 hours earlier and was meant to be parked at the depot."
        ),
        diagnosis=(
            "Active siphonage. Driver had detoured from the depot return route, "
            "parked at a coordinated meeting point, and transferred ~180L into a "
            "buyer's vehicle. Confirmed via covert camera installed after a prior "
            "suspected incident on the same vehicle."
        ),
        resolution=(
            "Driver dismissed; case filed with local police. Vehicle GPS lock-down "
            "enforced outside operating hours. ~180L recovered as restitution."
        ),
        lessons=[
            "Large fuel drops with engine off are almost never sensor noise — "
            "investigate every one above 20%",
            "Off-route night-time location is a stronger signal than time alone",
            "Distance from planned route at the time of the drop is highly diagnostic",
        ],
        tags=["night_event", "off_route", "engine_off", "ble_fuel_sensor"],
        confidence=0.98,
        occurred_at=datetime(2025, 8, 14, 2, 14),
    ),
    IncidentCase(
        case_id="fuel_theft_0002",
        category="fuel_theft",
        severity="medium",
        region="Kenya",
        vehicle_type="minitruck",
        summary=(
            "Fuel level rose 23% at GPS coordinates not in the fuel station registry. "
            "Refuel receipt submitted by driver claimed 40L purchased at a Total "
            "station 12km away. Vehicle was at coordinates -1.2933, 36.8219 at the "
            "claimed refuel time, not at the Total."
        ),
        diagnosis=(
            "Off-book refuel from an unlicensed jerrycan vendor. Driver pocketed "
            "the difference between the claimed station price and the actual lower "
            "informal-market price. Estimated loss: KES 800/refuel x ~3x/week."
        ),
        resolution=(
            "Verbal warning issued. Receipt verification process tightened — drivers "
            "now must photograph the station signage and pump display at refuel time."
        ),
        lessons=[
            "Cross-check claimed refuel locations against actual GPS coordinates at "
            "the receipt timestamp — mismatches are common",
            "Informal refuels are typically smaller (20-50L) than theft events",
            "Pattern emerges over weeks, not single incidents — track repeated mismatches",
        ],
        tags=["off_book_refuel", "receipt_mismatch", "daytime"],
        confidence=0.85,
        occurred_at=datetime(2025, 9, 3, 11, 47),
    ),
    IncidentCase(
        case_id="fuel_theft_0003",
        category="false_positive",
        severity="low",
        region="Zambia",
        vehicle_type="tanker",
        summary=(
            "Fuel level dropped 14% in 22 minutes while engine off. Vehicle was "
            "parked at the depot. Temperature dropped from 31C to 19C overnight "
            "during the same window."
        ),
        diagnosis=(
            "Sensor reading variation due to fuel thermal contraction. ~12% volume "
            "decrease is physically expected over a 12C drop in fuel temperature "
            "for diesel. Not theft."
        ),
        resolution=(
            "Detection threshold adjusted to account for ambient temperature delta "
            "when engine has been off for >2 hours. Vehicle calibration table "
            "annotated with this property."
        ),
        lessons=[
            "Overnight fuel-level drops in temperature-sensitive regions can be "
            "thermal, not theft — correlate with weather data",
            "Diesel volume changes ~0.08%/C; for a 12C drop on a 1000L tank, "
            "expect ~10L apparent loss",
            "Always rule out thermal effects before escalating overnight events",
        ],
        tags=["false_positive", "thermal_effect", "overnight"],
        confidence=0.95,
        occurred_at=datetime(2025, 7, 22, 5, 30),
    ),
    IncidentCase(
        case_id="fuel_theft_0004",
        category="fuel_theft",
        severity="critical",
        region="Nigeria",
        vehicle_type="long-haul truck",
        summary=(
            "Sustained fuel consumption rate of 78 L/100km over a 230km highway "
            "stretch, against the vehicle's normal 32 L/100km baseline. Driver "
            "reported standard highway driving, no unusual conditions."
        ),
        diagnosis=(
            "In-line siphon valve installed in the fuel return line. Driver was "
            "diverting fuel into a hidden auxiliary tank during the trip, then "
            "selling at destination. Mechanical inspection revealed the modification."
        ),
        resolution=(
            "Vehicle taken out of service for repair. Driver dismissed; criminal "
            "complaint filed. Hidden tank recovered ~340L. Fuel system tamper-"
            "detection seals now installed across the fleet."
        ),
        lessons=[
            "Consumption rate doubling or more, sustained over a long distance, is "
            "almost always mechanical siphonage — not driver behavior",
            "Compare actual L/100km against per-vehicle baseline, not fleet average",
            "Fuel system tamper-detection seals are cheap and prevent this entirely",
        ],
        tags=["mechanical_siphon", "consumption_anomaly", "highway"],
        confidence=0.99,
        occurred_at=datetime(2025, 6, 11, 14, 22),
    ),
    IncidentCase(
        case_id="fuel_theft_0005",
        category="fuel_theft",
        severity="medium",
        region="Mozambique",
        vehicle_type="beverage truck",
        summary=(
            "Fuel level dropped 11% in 8 minutes while engine state transitioned "
            "from running to idle. Location was a roadside lay-by near a market "
            "town at 13:45 local time. Two consecutive fuel drops in the same "
            "month at similar locations."
        ),
        diagnosis=(
            "Quick-siphon during lunch break — driver was selling small quantities "
            "(20-40L) to nearby informal sellers during normal-looking stops. "
            "Pattern only became visible by aggregating across multiple stops."
        ),
        resolution=(
            "Driver coached, lay-by stop detection added to live dashboard. "
            "Driver later transferred to a different route. Aggregate weekly "
            "fuel-drop tracking per driver instituted."
        ),
        lessons=[
            "Small individual drops can be invisible — aggregate them by driver "
            "and route over weeks",
            "Daytime theft tends to be smaller per-event but more frequent than night-time theft",
            "Coordinated multi-incident patterns require multi-day RAG retrieval, "
            "not just single-event context",
        ],
        tags=[
            "daytime",
            "small_volume",
            "repeat_offender",
            "pattern_only_visible_in_aggregate",
        ],
        confidence=0.88,
        occurred_at=datetime(2025, 10, 8, 13, 45),
    ),
]
