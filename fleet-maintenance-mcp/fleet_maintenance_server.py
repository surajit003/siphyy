"""
Fleet Maintenance MCP Server.

Exposes maintenance history and scheduling tools. Designed to run
alongside the fleet-tools server so Claude can orchestrate calls across
both based on what each tool's description matches.
"""

import logging
import sys
import uuid
from datetime import date, timedelta

from mcp.server.fastmcp import FastMCP
from mock_data import SERVICE_HISTORY, UPCOMING_SERVICES

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-7s [fleet-maintenance] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("fleet-maintenance")
log.info("starting fleet-maintenance MCP server")

mcp = FastMCP("fleet-maintenance")


@mcp.tool()
def get_maintenance_history(vehicle_id: str) -> list[dict]:
    """
    Return the past service and repair history for a vehicle.

    Use this when the user asks about past repairs, what's been done on
    a vehicle, brake/oil/engine work history, or wants a vehicle's
    service track record.

    Args:
        vehicle_id: Vehicle registration plate (e.g., 'KAY 234X').

    Returns:
        List of service records (id, service_type, performed_on,
        mileage_km, technician, notes), sorted newest first. Empty list
        if there's no history.
    """
    log.info("tool=get_maintenance_history vehicle_id=%r", vehicle_id)
    records = [s for s in SERVICE_HISTORY if s["vehicle_id"] == vehicle_id.upper()]
    records.sort(key=lambda r: r["performed_on"], reverse=True)
    log.debug("returning %d service record(s) for %s", len(records), vehicle_id.upper())
    return records


@mcp.tool()
def get_upcoming_services(vehicle_id: str | None = None, days: int = 30) -> list[dict]:
    """
    Return services scheduled to occur within the next N days.

    Use this when the user asks about upcoming maintenance, what's due,
    when a vehicle's next service is, or for fleet-wide service planning.

    Args:
        vehicle_id: Optional plate to filter by. If None, returns
                    upcoming services across the whole fleet.
        days: Look-ahead window in days (default 30).

    Returns:
        List of scheduled service records (id, vehicle_id, service_type,
        scheduled_date, garage, priority), sorted earliest first.
    """
    log.info("tool=get_upcoming_services vehicle_id=%r days=%d", vehicle_id, days)
    today = date.today()
    cutoff = today + timedelta(days=days)
    results = []
    for svc in UPCOMING_SERVICES:
        svc_date = date.fromisoformat(svc["scheduled_date"])
        if svc_date < today or svc_date > cutoff:
            continue
        if vehicle_id and svc["vehicle_id"] != vehicle_id.upper():
            continue
        results.append(svc)
    results.sort(key=lambda s: s["scheduled_date"])
    log.debug("returning %d upcoming service(s)", len(results))
    return results


@mcp.tool()
def schedule_service(
    vehicle_id: str,
    service_type: str,
    scheduled_date: str,
    garage: str = "TBD",
) -> dict:
    """
    Book a new scheduled service for a vehicle. WRITE tool — mutates
    fleet maintenance state.

    Use this when the user explicitly asks to schedule, book, or arrange
    a service. Confirm intent with the user before calling if there's any
    ambiguity.

    Args:
        vehicle_id: Vehicle registration plate.
        service_type: Free-text label (e.g., 'oil_change', 'tyre_rotation').
        scheduled_date: ISO-format date (YYYY-MM-DD).
        garage: Garage name (defaults to 'TBD' if the user hasn't picked one).

    Returns:
        The newly created service record with an auto-assigned id.
    """
    log.info(
        "tool=schedule_service vehicle_id=%r type=%r date=%r garage=%r",
        vehicle_id,
        service_type,
        scheduled_date,
        garage,
    )
    new_record = {
        "id": f"UPC-{uuid.uuid4().hex[:6].upper()}",
        "vehicle_id": vehicle_id.upper(),
        "service_type": service_type,
        "scheduled_date": scheduled_date,
        "garage": garage,
        "priority": "routine",
    }
    UPCOMING_SERVICES.append(new_record)
    log.info("created service record %s", new_record["id"])
    return new_record


if __name__ == "__main__":
    mcp.run()
