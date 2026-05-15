# Fleet Maintenance — MCP Server

A second Model Context Protocol server that runs alongside `fleet-tools`. Exposes vehicle maintenance history and scheduling, so Claude can orchestrate cross-server queries like "what's the status and next service of KAY 234X?"

## What it exposes

### Tools

| Name | Signature | Purpose |
|---|---|---|
| `get_maintenance_history` | `(vehicle_id: str) -> list[dict]` | Past service records for a vehicle, newest first. |
| `get_upcoming_services` | `(vehicle_id: str \| None = None, days: int = 30) -> list[dict]` | Services scheduled in the next N days, optionally filtered by vehicle. |
| `schedule_service` | `(vehicle_id: str, service_type: str, scheduled_date: str, garage: str = 'TBD') -> dict` | **Write tool** — books a new scheduled service. |

## Setup

```bash
uv venv --python 3.14
uv pip install -r requirements.txt
.venv/bin/python fleet_maintenance_server.py    # sanity check; Ctrl+C to stop
```

## Try cross-server queries

After registering both `fleet-tools` and `fleet-maintenance` with Claude Desktop, ask:

1. **"Show me the status and full maintenance history of KAY 234X."** — fires `get_vehicle_status` (fleet-tools) + `get_maintenance_history` (fleet-maintenance).
2. **"Which vehicle has a service due in the next week?"** — single-server: `get_upcoming_services(days=7)`.
3. **"KCA 891H had a recent incident. What service did it get afterwards?"** — chains `get_recent_incidents` + `get_maintenance_history`.
4. **"Schedule an oil change for KBJ 445T on 2026-05-25."** — write tool: `schedule_service`.
5. **"Summarise everything you know about KBJ 445T."** — wide cross-server query: status + incidents + history + upcoming.

The first time you ask one of these, watch BOTH log files in parallel:

```bash
tail -f ~/Library/Logs/Claude/mcp-server-fleet-tools.log \
       ~/Library/Logs/Claude/mcp-server-fleet-maintenance.log
```

You'll see tool calls landing on each server independently — that's Claude orchestrating across both.
