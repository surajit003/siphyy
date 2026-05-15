"""Mock data for the fleet MCP server. Replace with real DB queries later."""

VEHICLES = {
    "KAY 234X": {
        "driver": "Joseph Mwangi",
        "location": "Mombasa Rd, Km 32",
        "fuel_percent": 60,
        "speed_kph": 75,
        "last_update": "2026-05-15T14:32:00Z",
        "route": "Nairobi → Mombasa",
        "cargo_status": "intact",
    },
    "KCA 891H": {
        "driver": "Omar Hassan",
        "location": "Nyali Bridge, Mombasa",
        "fuel_percent": 25,
        "speed_kph": 0,
        "last_update": "2026-05-15T13:15:00Z",
        "route": "Mombasa → Malindi",
        "cargo_status": "intact",
    },
    "KBJ 445T": {
        "driver": "Grace Wanjiru",
        "location": "Westlands, Nairobi",
        "fuel_percent": 80,
        "speed_kph": 15,
        "last_update": "2026-05-15T14:30:00Z",
        "route": "Nairobi → Naivasha",
        "cargo_status": "intact",
    },
}

INCIDENTS = [
    {
        "id": "INC-001",
        "vehicle_id": "KAY 234X",
        "type": "speeding",
        "severity": "medium",
        "timestamp": "2026-05-13T16:00:00Z",
        "location": "Mlolongo - Athi River",
        "notes": "Exceeded 100kph on highway. No accident.",
    },
    {
        "id": "INC-002",
        "vehicle_id": "KCA 891H",
        "type": "mechanical",
        "severity": "high",
        "timestamp": "2026-05-14T11:20:00Z",
        "location": "Nyali Bridge",
        "notes": "Front tyre busted after pothole. Recovery dispatched.",
    },
    {
        "id": "INC-003",
        "vehicle_id": "KBJ 445T",
        "type": "delay",
        "severity": "low",
        "timestamp": "2026-05-15T09:45:00Z",
        "location": "Westlands",
        "notes": "ETA delayed 2hrs due to traffic congestion.",
    },
]
