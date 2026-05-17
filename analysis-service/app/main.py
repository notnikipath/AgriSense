from __future__ import annotations

from datetime import UTC, datetime
from statistics import mean
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from shared.agrisense_common import (
    CropType,
    FertilizerRecommendation,
    FieldStats,
    FieldStatsUpdateRequest,
    IrrigationRecommendation,
    Role,
    SensorThresholdCheckRequest,
    Settings,
    SoilType,
    ThresholdAlert,
    YieldForecast,
    check_sensor_threshold,
    fertilizer_need_kg_ha,
    forecast_yield_t_ha,
    has_permission,
    irrigation_need_liters_per_ha,
    optimize_crop_rotation,
    recommend_fertilizer_formula,
    recommend_irrigation_schedule,
    yield_mape,
)

settings = Settings(service_name="analysis-service", service_port=8403)
app = FastAPI(title="AgriSense Analysis Service", version="1.0.0")

field_stats: dict[str, FieldStats] = {
    "FIELD-DEMO-1": FieldStats(
        field_id="FIELD-DEMO-1",
        avg_moisture_pct=31.2,
        avg_temperature_c=24.8,
        avg_light_lux=45000,
    )
}
yield_predictions: list[float] = [5.6, 5.8, 6.1, 5.9]
yield_actuals: list[float] = [5.9, 5.7, 6.0, 6.2]
auto_irrigation_log: list[dict[str, Any]] = []
rotation_history: list[dict[str, Any]] = []


class IrrigationRequest(BaseModel):
    field_id: str
    crop_type: CropType
    avg_moisture_pct: float = Field(ge=0, le=100)
    temperature_c: float
    rainfall_mm: float = Field(default=0, ge=0)
    auto_mode: bool = False


class FertilizerRequest(BaseModel):
    field_id: str
    crop_type: CropType
    soil_type: SoilType
    target_yield_t_ha: float = Field(gt=0)
    ndvi: float = Field(ge=0, le=1)


class YieldForecastRequest(BaseModel):
    field_id: str
    season: str
    crop_type: CropType
    avg_moisture_pct: float = Field(ge=0, le=100)
    avg_temp_c: float
    light_lux: float = Field(ge=0)
    rainfall_mm: float = Field(ge=0)
    ndvi: float = Field(ge=0, le=1)
    actual_t_ha: float | None = Field(default=None, gt=0)


class CropRotationRequest(BaseModel):
    field_id: str
    current_crop: CropType
    soil_type: SoilType
    horizon_years: int = Field(default=3, ge=1, le=5)


IrrigationRequest.model_rebuild()
FertilizerRequest.model_rebuild()
YieldForecastRequest.model_rebuild()
CropRotationRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


def _upsert_field_stats(field_id: str, sensor_type: str, value: float) -> FieldStats:
    stats = field_stats.setdefault(
        field_id,
        FieldStats(field_id=field_id, avg_moisture_pct=0, avg_temperature_c=0, avg_light_lux=0),
    )
    alpha = 0.25
    if sensor_type == "soil_moisture":
        stats.avg_moisture_pct = round(stats.avg_moisture_pct * (1 - alpha) + value * alpha, 2)
    elif sensor_type == "temperature_c":
        stats.avg_temperature_c = round(stats.avg_temperature_c * (1 - alpha) + value * alpha, 2)
    else:
        stats.avg_light_lux = round(stats.avg_light_lux * (1 - alpha) + value * alpha, 2)
    stats.last_updated = datetime.now(UTC)
    return stats


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/analysis/sensor/check-threshold")
async def sensor_threshold(request: SensorThresholdCheckRequest) -> dict[str, Any]:
    finding = check_sensor_threshold(request.sensor_type, request.value)
    if not finding:
        return {"alert": None}
    alert = ThresholdAlert(
        alert_id=f"ALT-{uuid4().hex[:10].upper()}",
        field_id=request.field_id,
        sensor_id=request.sensor_id,
        severity=finding["severity"],
        message=finding["message"],
    )
    return {"alert": alert.model_dump(mode="json")}


@app.post("/analysis/fields/{field_id}/stats/update")
async def update_field_stats(field_id: str, request: FieldStatsUpdateRequest) -> dict[str, Any]:
    stats = _upsert_field_stats(field_id, request.sensor_type.value, request.value)
    return stats.model_dump(mode="json")


@app.get("/analysis/field-stats/{field_id}")
async def get_field_stats(field_id: str) -> dict[str, Any]:
    stats = field_stats.get(field_id)
    if stats is None:
        raise HTTPException(status_code=404, detail="Field stats not found")
    return stats.model_dump(mode="json")


@app.post("/analysis/irrigation")
async def irrigation_recommendation(request: IrrigationRequest) -> dict[str, Any]:
    liters = irrigation_need_liters_per_ha(request.avg_moisture_pct, request.temperature_c, request.crop_type)
    schedule = recommend_irrigation_schedule(
        request.avg_moisture_pct,
        request.temperature_c,
        request.rainfall_mm,
        request.crop_type,
    )
    rec = IrrigationRecommendation(
        field_id=request.field_id,
        liters_per_ha=liters,
        reason=f"moisture deficit with stress index {schedule['stress_index']}",
        auto_apply=request.auto_mode and liters > 0,
    )
    response = rec.model_dump(mode="json")
    response["schedule"] = schedule

    if rec.auto_apply:
        auto_irrigation_log.append(
            {
                "event_id": f"AUTO-{uuid4().hex[:8].upper()}",
                "field_id": request.field_id,
                "liters_per_ha": liters,
                "created_at": datetime.now(UTC).isoformat(),
            }
        )
    return response


@app.post("/analysis/fertilizer")
async def fertilizer_recommendation(request: FertilizerRequest) -> dict[str, Any]:
    dosage = fertilizer_need_kg_ha(request.crop_type, request.soil_type, request.target_yield_t_ha, request.ndvi)
    formula, focus = recommend_fertilizer_formula(request.crop_type, request.soil_type, request.ndvi)
    rec = FertilizerRecommendation(
        field_id=request.field_id,
        npk_formula=formula,
        dosage_kg_ha=dosage,
        rationale=f"focus={focus}, ndvi={request.ndvi}",
    )
    return rec.model_dump(mode="json")


@app.post("/analysis/yield-forecast")
async def yield_forecast(request: YieldForecastRequest) -> dict[str, Any]:
    predicted = forecast_yield_t_ha(
        request.crop_type,
        request.avg_moisture_pct,
        request.avg_temp_c,
        request.light_lux,
        request.rainfall_mm,
        request.ndvi,
    )
    forecast = YieldForecast(
        field_id=request.field_id,
        season=request.season,
        predicted_t_ha=predicted,
        confidence_pct=round(max(68.0, min(95.0, 74 + request.ndvi * 20)), 2),
    )
    yield_predictions.append(predicted)
    if request.actual_t_ha is not None:
        yield_actuals.append(request.actual_t_ha)

    return {
        "forecast": forecast.model_dump(mode="json"),
        "yield_mape_pct": yield_mape(
            yield_predictions[-min(len(yield_actuals), len(yield_predictions)) :],
            yield_actuals,
        ),
    }


@app.post("/analysis/crop-rotation/optimize")
async def crop_rotation(request: CropRotationRequest) -> dict[str, Any]:
    rotation = optimize_crop_rotation(request.current_crop, request.soil_type, request.horizon_years)
    payload = {
        "field_id": request.field_id,
        "current_crop": request.current_crop.value,
        "soil_type": request.soil_type.value,
        **rotation,
    }
    rotation_history.append(payload)
    return payload


@app.get("/analysis/auto-irrigation/log")
async def auto_irrigation_events(limit: int = 100) -> dict[str, Any]:
    return {"items": auto_irrigation_log[-limit:], "count": len(auto_irrigation_log)}


@app.get("/analysis/kpi")
async def kpi() -> dict[str, Any]:
    current_mape = yield_mape(
        yield_predictions[-min(len(yield_actuals), len(yield_predictions)):],
        yield_actuals,
    )
    moisture = [stats.avg_moisture_pct for stats in field_stats.values()]
    return {
        "yield_mape_pct": current_mape,
        "target_yield_mape_pct": settings.yield_mape_target,
        "avg_soil_moisture_pct": round(mean(moisture), 2) if moisture else 0.0,
    }
