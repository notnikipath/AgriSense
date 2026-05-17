from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from shared.agrisense_common import (
    DroneScan,
    FieldStats,
    Role,
    SensorDevice,
    SensorReading,
    SensorReadingBatch,
    SensorRegisterRequest,
    SensorType,
    Settings,
    WeatherSnapshot,
    build_audit_event,
    has_permission,
    sensor_latency_seconds,
    telemetry_realtime_plan,
)

settings = Settings(service_name="iot-service", service_port=8401)
app = FastAPI(title="AgriSense IoT Service", version="1.0.0")


def _default_thresholds(sensor_type: SensorType) -> tuple[float, float]:
    defaults = {
        SensorType.SOIL_MOISTURE: (24.0, 62.0),
        SensorType.TEMPERATURE_C: (7.0, 38.0),
        SensorType.LIGHT_LUX: (5000.0, 95000.0),
    }
    return defaults[sensor_type]


sensors: dict[str, SensorDevice] = {
    "SNS-DEMO-MOIST": SensorDevice(
        sensor_id="SNS-DEMO-MOIST",
        field_id="FIELD-DEMO-1",
        sensor_type=SensorType.SOIL_MOISTURE,
        threshold_low=24,
        threshold_high=62,
        installed_at=datetime.now(UTC) - timedelta(days=120),
    ),
    "SNS-DEMO-TEMP": SensorDevice(
        sensor_id="SNS-DEMO-TEMP",
        field_id="FIELD-DEMO-1",
        sensor_type=SensorType.TEMPERATURE_C,
        threshold_low=7,
        threshold_high=38,
        installed_at=datetime.now(UTC) - timedelta(days=120),
    ),
}
telemetry_store: dict[str, list[SensorReading]] = {
    "SNS-DEMO-MOIST": [
        SensorReading(
            sensor_id="SNS-DEMO-MOIST",
            field_id="FIELD-DEMO-1",
            sensor_type=SensorType.SOIL_MOISTURE,
            value=31.2,
            unit="%",
            timestamp=datetime.now(UTC) - timedelta(minutes=9),
        )
    ]
}
weather_store: dict[str, list[WeatherSnapshot]] = {
    "FIELD-DEMO-1": [
        WeatherSnapshot(
            field_id="FIELD-DEMO-1",
            timestamp=datetime.now(UTC) - timedelta(hours=1),
            temperature_c=24.8,
            humidity_pct=64,
            rainfall_mm=1.2,
            wind_mps=3.6,
        )
    ]
}
drone_scans: dict[str, list[DroneScan]] = {
    "FIELD-DEMO-1": [
        DroneScan(
            field_id="FIELD-DEMO-1",
            scan_id="DRN-DEMO-1",
            timestamp=datetime.now(UTC) - timedelta(hours=3),
            ndvi_mean=0.61,
            moisture_index=0.53,
            image_url="https://cdn.agrisense.local/scans/FIELD-DEMO-1.png",
        )
    ]
}
field_stats: dict[str, FieldStats] = {
    "FIELD-DEMO-1": FieldStats(
        field_id="FIELD-DEMO-1",
        avg_moisture_pct=31.2,
        avg_temperature_c=24.8,
        avg_light_lux=45000,
    )
}
alerts: list[dict[str, Any]] = []
audit_log: list[dict[str, Any]] = []


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _audit(actor_id: str, actor_role: Role, action: str, object_id: str, details: dict[str, Any] | None = None) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="iot",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


def _update_field_stats(reading: SensorReading) -> None:
    stats = field_stats.setdefault(
        reading.field_id,
        FieldStats(
            field_id=reading.field_id,
            avg_moisture_pct=0,
            avg_temperature_c=0,
            avg_light_lux=0,
        ),
    )
    alpha = 0.35
    if reading.sensor_type == SensorType.SOIL_MOISTURE:
        stats.avg_moisture_pct = round(stats.avg_moisture_pct * (1 - alpha) + reading.value * alpha, 2)
    elif reading.sensor_type == SensorType.TEMPERATURE_C:
        stats.avg_temperature_c = round(stats.avg_temperature_c * (1 - alpha) + reading.value * alpha, 2)
    else:
        stats.avg_light_lux = round(stats.avg_light_lux * (1 - alpha) + reading.value * alpha, 2)
    stats.last_updated = datetime.now(UTC)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/sensors")
async def list_sensors(field_id: str | None = None) -> dict[str, Any]:
    items = [
        sensor.model_dump(mode="json")
        for sensor in sensors.values()
        if not field_id or sensor.field_id == field_id
    ]
    return {"items": items, "count": len(items)}


@app.post("/sensors/register")
async def register_sensor(request: SensorRegisterRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "iot:register")
    sensor_id = f"SNS-{uuid4().hex[:8].upper()}"
    low, high = _default_thresholds(request.sensor_type)
    sensor = SensorDevice(
        sensor_id=sensor_id,
        field_id=request.field_id,
        sensor_type=request.sensor_type,
        threshold_low=request.threshold_low if request.threshold_low is not None else low,
        threshold_high=request.threshold_high if request.threshold_high is not None else high,
    )
    sensors[sensor_id] = sensor
    _audit(request.actor_id, request.actor_role, "iot.sensor.register", sensor_id)
    return sensor.model_dump(mode="json")


@app.post("/telemetry/ingest")
async def ingest_telemetry(request: SensorReadingBatch) -> dict[str, Any]:
    _assert_permission(request.actor_role, "iot:ingest")
    accepted = 0
    max_latency = 0.0
    triggered: list[dict[str, Any]] = []

    for reading in request.readings:
        device = sensors.get(reading.sensor_id)
        if device is None:
            low, high = _default_thresholds(reading.sensor_type)
            device = SensorDevice(
                sensor_id=reading.sensor_id,
                field_id=reading.field_id,
                sensor_type=reading.sensor_type,
                threshold_low=low,
                threshold_high=high,
            )
            sensors[reading.sensor_id] = device

        telemetry_store.setdefault(reading.sensor_id, []).append(reading)
        _update_field_stats(reading)
        accepted += 1

        latency = sensor_latency_seconds(reading.timestamp)
        max_latency = max(max_latency, latency)

        low = device.threshold_low
        high = device.threshold_high
        if low is not None and reading.value < low:
            triggered.append(
                {
                    "sensor_id": reading.sensor_id,
                    "field_id": reading.field_id,
                    "severity": "critical" if reading.sensor_type == SensorType.SOIL_MOISTURE else "warning",
                    "message": f"{reading.sensor_type.value} below threshold {low}",
                }
            )
        if high is not None and reading.value > high:
            triggered.append(
                {
                    "sensor_id": reading.sensor_id,
                    "field_id": reading.field_id,
                    "severity": "critical" if reading.sensor_type == SensorType.TEMPERATURE_C else "warning",
                    "message": f"{reading.sensor_type.value} above threshold {high}",
                }
            )

    if triggered:
        alerts.extend(triggered)

    return {
        "accepted": accepted,
        "alerts": triggered,
        "max_latency_seconds": round(max_latency, 3),
    }


@app.get("/telemetry/{sensor_id}")
async def sensor_feed(sensor_id: str, limit: int = 100) -> dict[str, Any]:
    items = [point.model_dump(mode="json") for point in telemetry_store.get(sensor_id, [])][-limit:]
    return {"sensor_id": sensor_id, "items": items, "count": len(items)}


@app.post("/weather/ingest")
async def ingest_weather(snapshot: WeatherSnapshot) -> dict[str, Any]:
    weather_store.setdefault(snapshot.field_id, []).append(snapshot)
    return snapshot.model_dump(mode="json")


@app.post("/drone/ingest")
async def ingest_drone_scan(scan: DroneScan) -> dict[str, Any]:
    drone_scans.setdefault(scan.field_id, []).append(scan)
    return scan.model_dump(mode="json")


@app.get("/fields/{field_id}/snapshot")
async def field_snapshot(field_id: str) -> dict[str, Any]:
    latest_weather = (
        weather_store.get(field_id, [])[-1].model_dump(mode="json") if weather_store.get(field_id) else None
    )
    latest_scan = drone_scans.get(field_id, [])[-1].model_dump(mode="json") if drone_scans.get(field_id) else None
    stats = field_stats.get(field_id)
    return {
        "field_id": field_id,
        "sensor_count": len([sensor for sensor in sensors.values() if sensor.field_id == field_id]),
        "stats": stats.model_dump(mode="json") if stats else None,
        "latest_weather": latest_weather,
        "latest_drone_scan": latest_scan,
    }


@app.get("/alerts")
async def alert_history(limit: int = 200) -> dict[str, Any]:
    return {"items": alerts[-limit:], "count": len(alerts)}


@app.get("/processing/realtime-plan")
async def realtime_plan(sensor_count: int = 10000, regions: int = 8) -> dict[str, int]:
    return telemetry_realtime_plan(sensor_count, regions)


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}
