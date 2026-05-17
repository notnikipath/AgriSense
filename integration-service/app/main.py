from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from shared.agrisense_common import (
    IntegrationSyncRequest,
    IntegrationSyncResult,
    Role,
    Settings,
    build_audit_event,
    has_permission,
    map_cache_tiles_estimate,
    offline_pack_size_mb,
)

settings = Settings(service_name="integration-service", service_port=8406)
app = FastAPI(title="AgriSense Integration Service", version="1.0.0")

sync_history: list[IntegrationSyncResult] = [
    IntegrationSyncResult(
        sync_id="SYNC-DEMO-1",
        system_name="gps",
        status="ok",
        details={"provider": "agri-gps", "machines": 48},
    )
]
weather_latest: dict[str, dict[str, Any]] = {
    "FIELD-DEMO-1": {
        "field_id": "FIELD-DEMO-1",
        "provider": "open-meteo",
        "temperature_c": 23.6,
        "rainfall_mm": 0.8,
        "humidity_pct": 61,
        "wind_mps": 3.4,
        "captured_at": datetime.now(UTC).isoformat(),
    }
}
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
            object_type="integration",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


def _register_sync(system_name: str, details: dict[str, Any], actor_id: str, actor_role: Role) -> dict[str, Any]:
    result = IntegrationSyncResult(sync_id=str(uuid4()), system_name=system_name, status="ok", details=details)
    sync_history.append(result)
    _audit(actor_id, actor_role, f"integration.{system_name}.sync", result.sync_id, details)
    return result.model_dump(mode="json")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/integrations/sync")
async def generic_sync(request: IntegrationSyncRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "integration:manage")
    return _register_sync(request.system_name, request.payload, request.actor_id, request.actor_role)


@app.post("/integrations/gps/sync")
async def gps_sync(request: IntegrationSyncRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "integration:manage")
    details = {
        "provider": "AgriGPS",
        "machines": request.payload.get("machines", 120),
        "active_tracks": request.payload.get("active_tracks", 5600),
    }
    return _register_sync("gps", details, request.actor_id, request.actor_role)


@app.post("/integrations/agrochem/sync")
async def agrochem_sync(request: IntegrationSyncRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "integration:manage")
    details = {
        "supplier": request.payload.get("supplier", "AgroChem Union"),
        "items": request.payload.get("items", 24),
        "direction": request.payload.get("direction", "import"),
    }
    return _register_sync("agrochem", details, request.actor_id, request.actor_role)


@app.post("/integrations/weather/fetch")
async def weather_fetch(request: IntegrationSyncRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "integration:manage")
    field_id = str(request.payload.get("field_id", "FIELD-DEMO-1"))
    temperature = float(request.payload.get("temperature_c", 22.4))
    rainfall = float(request.payload.get("rainfall_mm", 1.1))
    humidity = float(request.payload.get("humidity_pct", 58.0))
    wind = float(request.payload.get("wind_mps", 4.0))

    weather_payload = {
        "field_id": field_id,
        "provider": "open-meteo",
        "temperature_c": temperature,
        "rainfall_mm": rainfall,
        "humidity_pct": humidity,
        "wind_mps": wind,
        "captured_at": datetime.now(UTC).isoformat(),
    }
    weather_latest[field_id] = weather_payload
    _register_sync("weather", weather_payload, request.actor_id, request.actor_role)
    return weather_payload


@app.get("/integrations/weather/latest/{field_id}")
async def weather_latest_for_field(field_id: str) -> dict[str, Any]:
    payload = weather_latest.get(field_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Weather data not found")
    return payload


@app.get("/mobile/offline-maps/{field_id}")
async def offline_maps(field_id: str, area_ha: float = 100, zoom: int = 16) -> dict[str, Any]:
    tiles = map_cache_tiles_estimate(area_ha, zoom)
    size_mb = offline_pack_size_mb(area_ha, zoom)
    return {
        "field_id": field_id,
        "format": "mbtiles",
        "tile_count": tiles,
        "estimated_size_mb": size_mb,
        "download_path": f"/downloads/{field_id}-z{zoom}.mbtiles",
    }


@app.get("/integrations/history")
async def history(system_name: str | None = None) -> dict[str, Any]:
    items = [
        item.model_dump(mode="json")
        for item in sync_history
        if not system_name or item.system_name == system_name
    ]
    return {"items": items, "count": len(items)}


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}
