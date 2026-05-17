from datetime import UTC, datetime, timedelta
from pathlib import Path

from fastapi.testclient import TestClient

from tests.integration.helpers import load_module

ROOT = Path(__file__).resolve().parents[2]

iot_module = load_module("iot_module", ROOT / "iot-service" / "app" / "main.py")
field_module = load_module("field_module", ROOT / "field-service" / "app" / "main.py")
analysis_module = load_module("analysis_module", ROOT / "analysis-service" / "app" / "main.py")
planning_module = load_module("planning_module", ROOT / "planning-service" / "app" / "main.py")
analytics_module = load_module("analytics_module", ROOT / "analytics-service" / "app" / "main.py")
integration_module = load_module("integration_module", ROOT / "integration-service" / "app" / "main.py")
notification_module = load_module("notification_module", ROOT / "notification-service" / "app" / "main.py")

iot_client = TestClient(iot_module.app)
field_client = TestClient(field_module.app)
analysis_client = TestClient(analysis_module.app)
planning_client = TestClient(planning_module.app)
analytics_client = TestClient(analytics_module.app)
integration_client = TestClient(integration_module.app)
notification_client = TestClient(notification_module.app)


def test_iot_analysis_notification_workflow() -> None:
    reading_ts = (datetime.now(UTC) - timedelta(seconds=3)).isoformat()
    ingest = iot_client.post(
        "/telemetry/ingest",
        json={
            "readings": [
                {
                    "sensor_id": "SNS-DEMO-MOIST",
                    "field_id": "FIELD-DEMO-1",
                    "sensor_type": "soil_moisture",
                    "value": 18.0,
                    "unit": "%",
                    "timestamp": reading_ts,
                }
            ],
            "actor_role": "operator",
        },
    )
    assert ingest.status_code == 200
    assert ingest.json()["accepted"] == 1

    threshold = analysis_client.post(
        "/analysis/sensor/check-threshold",
        json={
            "sensor_id": "SNS-DEMO-MOIST",
            "field_id": "FIELD-DEMO-1",
            "sensor_type": "soil_moisture",
            "value": 18.0,
        },
    )
    assert threshold.status_code == 200
    alert = threshold.json()["alert"]
    assert alert is not None

    update_stats = analysis_client.post(
        "/analysis/fields/FIELD-DEMO-1/stats/update",
        json={
            "sensor_id": "SNS-DEMO-MOIST",
            "field_id": "FIELD-DEMO-1",
            "sensor_type": "soil_moisture",
            "value": 18.0,
        },
    )
    assert update_stats.status_code == 200
    assert update_stats.json()["field_id"] == "FIELD-DEMO-1"

    notify = notification_client.post(
        "/notify/agronomist-alert",
        json={
            "field_id": "FIELD-DEMO-1",
            "sensor_id": "SNS-DEMO-MOIST",
            "severity": "critical",
            "message": "soil moisture below threshold",
            "actor_role": "agronomist",
        },
    )
    assert notify.status_code == 200

    task = planning_client.post(
        "/tasks",
        json={
            "field_id": "FIELD-DEMO-1",
            "work_type": "irrigation",
            "planned_start": datetime.now(UTC).isoformat(),
            "planned_end": (datetime.now(UTC) + timedelta(hours=5)).isoformat(),
            "assignee": "brigade.north",
            "machinery": "Pivot-01",
            "actor_id": "MNG-001",
            "actor_role": "manager",
        },
    )
    assert task.status_code == 200

    latency = analytics_client.post("/analytics/ingest/sensor-latency", json={"latency_seconds": 3.8})
    assert latency.status_code == 200
    kpi = analytics_client.get("/analytics/kpi", params={"actor_role": "manager"})
    assert kpi.status_code == 200
    assert "yield_mape_pct" in kpi.json()


def test_field_integration_and_analytics_flow() -> None:
    field = field_client.get("/fields/FIELD-DEMO-1")
    assert field.status_code == 200

    treatment = field_client.post(
        "/fields/FIELD-DEMO-1/treatments",
        json={
            "work_type": "fertilization",
            "fertilizer_kg_ha": 36,
            "irrigation_mm": 0,
            "note": "NPK top dressing",
            "actor_id": "AGR-001",
            "actor_role": "agronomist",
        },
    )
    assert treatment.status_code == 200

    first_cache = field_client.get("/maps/cache/tiles", params={"field_id": "FIELD-DEMO-1", "zoom": 16})
    second_cache = field_client.get("/maps/cache/tiles", params={"field_id": "FIELD-DEMO-1", "zoom": 16})
    assert first_cache.status_code == 200
    assert second_cache.status_code == 200
    assert second_cache.json()["cached"] is True

    weather = integration_client.post(
        "/integrations/weather/fetch",
        json={
            "system_name": "weather",
            "payload": {
                "field_id": "FIELD-DEMO-1",
                "temperature_c": 25.1,
                "rainfall_mm": 1.5,
                "humidity_pct": 58,
                "wind_mps": 4.2,
            },
            "actor_id": "MNG-001",
            "actor_role": "manager",
        },
    )
    assert weather.status_code == 200

    offline_pack = integration_client.get(
        "/mobile/offline-maps/FIELD-DEMO-1",
        params={"area_ha": 128.4, "zoom": 16},
    )
    assert offline_pack.status_code == 200
    assert offline_pack.json()["estimated_size_mb"] > 0

    ingest_yield = analytics_client.post(
        "/analytics/ingest/yield",
        json={
            "field_id": "FIELD-DEMO-1",
            "year": 2025,
            "predicted_t_ha": 6.0,
            "actual_t_ha": 5.8,
            "revenue_rub": 9_100_000,
            "cost_rub": 5_460_000,
        },
    )
    assert ingest_yield.status_code == 200

    yearly = analytics_client.get("/analytics/yield/comparison")
    assert yearly.status_code == 200
    assert yearly.json()["items"]
