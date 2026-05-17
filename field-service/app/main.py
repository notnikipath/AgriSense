from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.agrisense_common import (
    CropType,
    FieldCreateRequest,
    FieldProfile,
    FieldZone,
    GeoPoint,
    Role,
    Settings,
    SoilType,
    TreatmentRecord,
    TTLCache,
    WorkType,
    build_audit_event,
    has_permission,
    map_cache_tiles_estimate,
)

settings = Settings(service_name="field-service", service_port=8402)
app = FastAPI(title="AgriSense Field Service", version="1.0.0")

fields: dict[str, FieldProfile] = {
    "FIELD-DEMO-1": FieldProfile(
        field_id="FIELD-DEMO-1",
        name="North Wheat Block",
        region="Tula",
        crop_type=CropType.WHEAT,
        area_ha=128.4,
        boundary=[
            GeoPoint(latitude=54.2134, longitude=37.6191),
            GeoPoint(latitude=54.2198, longitude=37.6581),
            GeoPoint(latitude=54.1965, longitude=37.6779),
            GeoPoint(latitude=54.1871, longitude=37.6424),
        ],
        zones=[
            FieldZone(zone_id="Z1", soil_type=SoilType.CHERNOZEM, area_ha=54.2, ph=6.7, organic_matter_pct=4.1),
            FieldZone(zone_id="Z2", soil_type=SoilType.LOAM, area_ha=42.6, ph=6.4, organic_matter_pct=3.3),
            FieldZone(zone_id="Z3", soil_type=SoilType.SANDY, area_ha=31.6, ph=6.1, organic_matter_pct=2.2),
        ],
        treatment_history=[
            TreatmentRecord(
                event_id="TRT-DEMO-1",
                field_id="FIELD-DEMO-1",
                work_type=WorkType.SOWING,
                fertilizer_kg_ha=42,
                irrigation_mm=0,
                date=datetime.now(UTC),
                note="Spring sowing campaign",
            )
        ],
    )
}
map_cache = TTLCache(ttl_seconds=900)
map_cache_stats = {"hits": 0, "misses": 0}
audit_log: list[dict[str, Any]] = []


class TreatmentCreateRequest(BaseModel):
    work_type: WorkType
    fertilizer_kg_ha: float = Field(default=0, ge=0)
    irrigation_mm: float = Field(default=0, ge=0)
    note: str = ""
    actor_id: str
    actor_role: Role


TreatmentCreateRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _audit(actor_id: str, actor_role: Role, action: str, object_id: str, details: dict[str, Any] | None = None) -> None:
    audit_log.append(
        build_audit_event(
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            object_type="field",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/fields")
async def list_fields(crop_type: CropType | None = None) -> dict[str, Any]:
    items = []
    for field in fields.values():
        if crop_type and field.crop_type != crop_type:
            continue
        items.append(field.model_dump(mode="json"))
    return {"items": items, "count": len(items)}


@app.get("/fields/{field_id}")
async def get_field(field_id: str) -> dict[str, Any]:
    field = fields.get(field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")
    return field.model_dump(mode="json")


@app.post("/fields")
async def create_field(request: FieldCreateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "field:update")
    field_id = f"FIELD-{uuid4().hex[:8].upper()}"
    field = FieldProfile(
        field_id=field_id,
        name=request.name,
        region=request.region,
        crop_type=request.crop_type,
        area_ha=request.area_ha,
        boundary=request.boundary,
        zones=request.zones,
    )
    fields[field_id] = field
    _audit(request.actor_id, request.actor_role, "field.create", field_id)
    return field.model_dump(mode="json")


@app.post("/fields/{field_id}/treatments")
async def add_treatment(field_id: str, request: TreatmentCreateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "field:update")
    field = fields.get(field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")
    event = TreatmentRecord(
        event_id=f"TRT-{uuid4().hex[:10].upper()}",
        field_id=field_id,
        work_type=request.work_type,
        fertilizer_kg_ha=request.fertilizer_kg_ha,
        irrigation_mm=request.irrigation_mm,
        note=request.note,
    )
    field.treatment_history.append(event)
    _audit(request.actor_id, request.actor_role, "field.treatment.add", event.event_id, {"field_id": field_id})
    return event.model_dump(mode="json")


@app.get("/fields/{field_id}/history")
async def treatment_history(field_id: str) -> dict[str, Any]:
    field = fields.get(field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")
    items = [item.model_dump(mode="json") for item in field.treatment_history]
    return {"items": items, "count": len(items)}


@app.get("/fields/{field_id}/soil-zones")
async def soil_zones(field_id: str) -> dict[str, Any]:
    field = fields.get(field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")
    return {"items": [zone.model_dump(mode="json") for zone in field.zones], "count": len(field.zones)}


@app.get("/maps/cache/tiles")
async def map_tiles(field_id: str, zoom: int = 16) -> dict[str, Any]:
    field = fields.get(field_id)
    if field is None:
        raise HTTPException(status_code=404, detail="Field not found")
    cache_key = f"{field_id}:{zoom}"
    cached = map_cache.get(cache_key)
    if cached is not None:
        map_cache_stats["hits"] += 1
        return {"field_id": field_id, "zoom": zoom, "cached": True, **cached}

    tile_count = map_cache_tiles_estimate(field.area_ha, zoom)
    payload = {
        "tile_count": tile_count,
        "provider": "postgis-vector-cache",
        "expires_in_seconds": map_cache.ttl,
    }
    map_cache.set(cache_key, payload)
    map_cache_stats["misses"] += 1
    return {"field_id": field_id, "zoom": zoom, "cached": False, **payload}


@app.get("/maps/cache/stats")
async def cache_stats() -> dict[str, Any]:
    return {
        "hits": map_cache_stats["hits"],
        "misses": map_cache_stats["misses"],
        "hit_ratio": round(
            map_cache_stats["hits"] / max(map_cache_stats["hits"] + map_cache_stats["misses"], 1),
            3,
        ),
    }


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}
