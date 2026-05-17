from __future__ import annotations

import json
import urllib.request
from datetime import UTC, datetime, timedelta

BASE = "http://localhost:8580"


def request(method: str, path: str, payload: dict | None = None) -> dict:
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    sensor_workflow = request(
        "POST",
        "/workflow/process-sensor",
        {
            "sensor_id": "SNS-DEMO-MOIST",
            "field_id": "FIELD-DEMO-1",
            "sensor_type": "soil_moisture",
            "value": 21.5,
            "unit": "%",
            "timestamp": (datetime.now(UTC) - timedelta(seconds=2)).isoformat(),
        },
    )
    print("Sensor workflow result:")
    print(json.dumps(sensor_workflow, ensure_ascii=False, indent=2))

    planning_workflow = request(
        "POST",
        "/workflow/plan-field-work",
        {
            "field_id": "FIELD-DEMO-1",
            "crop_type": "wheat",
            "soil_type": "chernozem",
            "target_yield_t_ha": 6.3,
            "ndvi": 0.62,
            "moisture_pct": 30.4,
            "temperature_c": 26.0,
            "rainfall_mm": 0.6,
            "actor_id": "MNG-001",
            "actor_role": "manager",
        },
    )
    print("\nField work workflow result:")
    print(json.dumps(planning_workflow, ensure_ascii=False, indent=2))
