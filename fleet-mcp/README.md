# Fleet Tools — MCP Server

A small Model Context Protocol (MCP) server that exposes fleet-management tools and resources to MCP clients like Claude Code, Claude Desktop, or claude.ai (via a remote runner). Mock data for now; wire to real Postgres later.

## What it exposes

### Tools

| Name | Signature | Purpose |
|---|---|---|
| `get_vehicle_status` | `(vehicle_id: str) -> dict` | Current status of one vehicle: location, fuel, driver, speed, route, cargo, last_update. |
| `list_vehicles` | `() -> list[dict]` | All vehicles in the fleet with driver + route. Useful as a discovery step before other calls. |
| `get_recent_incidents` | `(vehicle_id: str \| None = None, days: int = 7) -> list[dict]` | Recent incidents, optionally filtered by vehicle, within a lookback window. |

### Resources

| URI | Purpose |
|---|---|
| `fleet://vehicles/all` | JSON snapshot of every vehicle with full state. Use this when the client wants to read fleet state directly rather than via a tool call. |

## Setup

From this directory. Requires `uv` (the package manager) — `brew install uv` if you don't have it.

```bash
# 1. Create a venv with Python 3.14 (the latest stable at time of writing).
#    `uv venv` works regardless of whether your system `python3` is recent
#    enough or has ensurepip available — it handles both itself.
uv venv --python 3.14

# 2. Install the MCP SDK
uv pip install -r requirements.txt

# 3. Sanity-check the server starts (Ctrl+C to stop — it waits for stdio)
.venv/bin/python fleet_mcp_server.py
```

### Register with Claude Code

The intent: register a server named `fleet-tools` that runs `fleet_mcp_server.py` with the venv's Python so the `mcp` package is available. Use absolute paths.

```bash
claude mcp add fleet-tools \
  --scope local \
  -- \
  /absolute/path/to/fleet-mcp/.venv/bin/python \
  /absolute/path/to/fleet-mcp/fleet_mcp_server.py
```

Verify:

```bash
claude mcp list
# Should show: fleet-tools
```

If the CLI syntax has shifted since this was written, run `claude mcp --help` and adapt — the only thing that matters is that Claude Code launches the venv's Python with the server script.

## Try it in Claude Code

Open a fresh Claude Code session and try these queries — they exercise different tools and tool-chaining:

1. **"What vehicles are in my fleet?"** — calls `list_vehicles`.
2. **"What's the status of KAY 234X?"** — calls `get_vehicle_status`.
3. **"Which vehicle has the lowest fuel right now?"** — calls `list_vehicles` then `get_vehicle_status` for each, or reads `fleet://vehicles/all` directly.
4. **"Were there any incidents in the last 5 days?"** — calls `get_recent_incidents(days=5)`.
5. **"KCA 891H has low fuel. What's the most recent incident on that vehicle and what should I do?"** — chains `get_vehicle_status` + `get_recent_incidents(vehicle_id="KCA 891H")` then reasons over both.

If the model doesn't volunteer to use the tools, prompt explicitly: *"Use the fleet-tools MCP server."*

## Next steps

Things this scaffolding is deliberately too small for; pick them up when you're ready:

- **Wire to real Postgres.** Replace `mock_data.py` with a thin `db.py` that queries actual tables. Tools keep the same signatures; their bodies change.
- **Add a write tool: `create_incident`.** Demonstrates the read/write distinction in MCP — write tools should be opt-in, logged, and ideally idempotent.
- **Add an MCP prompt template.** `@mcp.prompt()` lets you ship reusable prompt scaffolding to clients ("summarise today's fleet status as a daily standup"). Useful for ops workflows.
