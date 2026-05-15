"""
Fleet Tools MCP Server.

Exposes fleet management tools and resources to MCP clients
(Claude Code, Claude Desktop, claude.ai via remote, etc.).
Mock data for now — wire to real Postgres later.
"""

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from mcp.server.fastmcp import FastMCP

from mock_data import VEHICLES, INCIDENTS

# MCP servers speak the protocol on stdout — anything printed there gets
# parsed as a protocol message and will corrupt the session. ALL diagnostic
# output must go to stderr. Python's logging defaults to stderr, but we set
# it explicitly so future changes can't accidentally redirect to stdout.
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-7s [fleet-tools] %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("fleet-tools")
log.info("starting fleet-tools MCP server")

mcp = FastMCP("fleet-tools")


@mcp.tool()
def get_vehicle_status(vehicle_id: str) -> dict:
    """
    Return current status of a fleet vehicle: location, fuel, driver, route.

    Args:
        vehicle_id: Vehicle registration plate (e.g., 'KAY 234X')

    Returns:
        Status dict with location, fuel_percent, driver, speed_kph, route,
        cargo_status, last_update. Returns error dict if vehicle not found.
    """
    log.info("tool=get_vehicle_status vehicle_id=%r", vehicle_id)
    vehicle = VEHICLES.get(vehicle_id.upper())
    if not vehicle:
        log.warning("vehicle not found: %s", vehicle_id)
        return {"error": f"Vehicle {vehicle_id} not found in fleet"}
    log.debug("returning status for %s", vehicle_id.upper())
    return {"vehicle_id": vehicle_id.upper(), **vehicle}


@mcp.tool()
def list_vehicles() -> list[dict]:
    """
    List all vehicles currently in the fleet with driver and route info.

    Use this when you need to know which vehicles exist before calling
    other tools, or for fleet-wide queries.
    """
    log.info("tool=list_vehicles count=%d", len(VEHICLES))
    return [
        {"vehicle_id": vid, "driver": v["driver"], "route": v["route"]}
        for vid, v in VEHICLES.items()
    ]


@mcp.tool()
def get_recent_incidents(vehicle_id: str | None = None, days: int = 7) -> list[dict]:
    """
    Get recent fleet incidents within the last N days.

    Args:
        vehicle_id: Optional vehicle filter. If None, returns incidents
                    across all vehicles.
        days: Look-back window in days (default 7).

    Returns:
        List of incident records (id, type, severity, location, notes,
        timestamp, vehicle_id).
    """
    log.info("tool=get_recent_incidents vehicle_id=%r days=%d", vehicle_id, days)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    results = []
    for inc in INCIDENTS:
        inc_time = datetime.fromisoformat(inc["timestamp"].replace("Z", "+00:00"))
        if inc_time < cutoff:
            continue
        if vehicle_id and inc["vehicle_id"] != vehicle_id.upper():
            continue
        results.append(inc)
    log.debug("returning %d incident(s)", len(results))
    return results


@mcp.resource("fleet://vehicles/all")
def all_vehicles_resource() -> str:
    """A complete snapshot of all vehicles in the fleet with current state."""
    log.info("resource=fleet://vehicles/all requested")
    return json.dumps(VEHICLES, indent=2)


if __name__ == "__main__":
    mcp.run()
