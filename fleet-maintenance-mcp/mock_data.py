"""Mock data for the fleet maintenance MCP server."""

SERVICE_HISTORY = [
    {
        "id": "SVC-001", "vehicle_id": "KAY 234X",
        "service_type": "oil_change",
        "performed_on": "2026-04-12",
        "mileage_km": 248_500,
        "technician": "Auto Care Nairobi",
        "notes": "Routine 10k oil change. Brake pads still ok.",
    },
    {
        "id": "SVC-002", "vehicle_id": "KAY 234X",
        "service_type": "brake_replacement",
        "performed_on": "2025-12-15",
        "mileage_km": 236_200,
        "technician": "Auto Care Nairobi",
        "notes": "Front brake pads replaced. Rear pads ~30% life remaining.",
    },
    {
        "id": "SVC-003", "vehicle_id": "KCA 891H",
        "service_type": "tyre_replacement",
        "performed_on": "2026-05-14",
        "mileage_km": 189_300,
        "technician": "Tyre Centre Mombasa",
        "notes": "Front-left replaced after pothole damage (incident INC-002).",
    },
    {
        "id": "SVC-004", "vehicle_id": "KCA 891H",
        "service_type": "engine_tune",
        "performed_on": "2025-09-20",
        "mileage_km": 178_400,
        "technician": "Mombasa Motor Works",
        "notes": "Full engine tune. Belts replaced.",
    },
    {
        "id": "SVC-005", "vehicle_id": "KBJ 445T",
        "service_type": "clutch_replacement",
        "performed_on": "2025-11-08",
        "mileage_km": 145_700,
        "technician": "Westlands Garage",
        "notes": "Clutch replaced. Driver reported smoother shifts.",
    },
]

UPCOMING_SERVICES = [
    {
        "id": "UPC-001", "vehicle_id": "KBJ 445T",
        "service_type": "90_day_service",
        "scheduled_date": "2026-05-20",
        "garage": "Westlands Garage",
        "priority": "routine",
    },
    {
        "id": "UPC-002", "vehicle_id": "KCA 891H",
        "service_type": "full_inspection",
        "scheduled_date": "2026-06-01",
        "garage": "Mombasa Motor Works",
        "priority": "high",
    },
    {
        "id": "UPC-003", "vehicle_id": "KAY 234X",
        "service_type": "90_day_service",
        "scheduled_date": "2026-07-12",
        "garage": "Auto Care Nairobi",
        "priority": "routine",
    },
]
