from __future__ import annotations

import json
import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

CROPS = ["wheat", "corn", "vegetables", "fruit_trees", "technical"]
SENSOR_TYPES = ["soil_moisture", "temperature_c", "light_lux"]
REGIONS = ["Tula", "Kursk", "Voronezh", "Belgorod", "Krasnodar", "Saratov"]


def generate_record(index: int) -> dict:
    sensor_type = random.choice(SENSOR_TYPES)
    if sensor_type == "soil_moisture":
        value = round(random.uniform(16, 58), 2)
        unit = "%"
    elif sensor_type == "temperature_c":
        value = round(random.uniform(8, 39), 2)
        unit = "C"
    else:
        value = round(random.uniform(6000, 82000), 2)
        unit = "lux"

    return {
        "event_id": f"EVT-{index:05d}",
        "sensor_id": f"SNS-{random.randint(1, 12000):05d}",
        "field_id": f"FIELD-{random.randint(1, 500):04d}",
        "crop_type": random.choice(CROPS),
        "region": random.choice(REGIONS),
        "sensor_type": sensor_type,
        "value": value,
        "unit": unit,
        "ndvi": round(random.uniform(0.35, 0.82), 3),
        "rainfall_mm": round(random.uniform(0, 6.5), 2),
        "created_at": (datetime.now(UTC) - timedelta(seconds=index)).isoformat(),
    }


if __name__ == "__main__":
    random.seed(42)
    output = Path(__file__).resolve().parents[1] / "data" / "samples" / "agri_events.json"
    payload = [generate_record(index) for index in range(1, 12001)]
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload)} records to {output}")
