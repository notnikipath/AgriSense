from __future__ import annotations

from statistics import mean
from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from shared.agrisense_common import (
    Role,
    Settings,
    economic_margin_pct,
    has_permission,
    telemetry_realtime_plan,
    yearly_yield_summary,
    yield_mape,
)

settings = Settings(service_name="analytics-service", service_port=8405)
app = FastAPI(title="AgriSense Analytics Service", version="1.0.0")

yield_records: list[dict[str, Any]] = [
    {
        "field_id": "FIELD-DEMO-1",
        "year": 2023,
        "predicted_t_ha": 5.7,
        "actual_t_ha": 5.9,
        "revenue_rub": 8_620_000,
        "cost_rub": 5_120_000,
    },
    {
        "field_id": "FIELD-DEMO-1",
        "year": 2024,
        "predicted_t_ha": 6.0,
        "actual_t_ha": 6.1,
        "revenue_rub": 8_980_000,
        "cost_rub": 5_240_000,
    },
]
sensor_latencies: list[float] = [2.1, 3.4, 1.8, 4.2]


class YieldIngestRequest(BaseModel):
    field_id: str
    year: int = Field(ge=2015, le=2100)
    predicted_t_ha: float = Field(gt=0)
    actual_t_ha: float = Field(gt=0)
    revenue_rub: float = Field(ge=0)
    cost_rub: float = Field(ge=0)


class LatencyIngestRequest(BaseModel):
    latency_seconds: float = Field(ge=0)
    sensor_id: str | None = None


YieldIngestRequest.model_rebuild()
LatencyIngestRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot perform {action}")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/analytics/ingest/yield")
async def ingest_yield(request: YieldIngestRequest) -> dict[str, Any]:
    row = request.model_dump(mode="json")
    yield_records.append(row)
    predicted = [item["predicted_t_ha"] for item in yield_records]
    actual = [item["actual_t_ha"] for item in yield_records]
    return {
        "status": "accepted",
        "yield_mape_pct": yield_mape(predicted, actual),
        "records": len(yield_records),
    }


@app.post("/analytics/ingest/sensor-latency")
async def ingest_latency(request: LatencyIngestRequest) -> dict[str, Any]:
    sensor_latencies.append(request.latency_seconds)
    return {"status": "accepted", "avg_latency_seconds": round(mean(sensor_latencies), 3)}


@app.get("/analytics/yield/comparison")
async def yearly_comparison() -> dict[str, Any]:
    return {"items": yearly_yield_summary(yield_records), "count": len(yield_records)}


@app.get("/analytics/economics")
async def economics() -> dict[str, Any]:
    revenue = sum(item["revenue_rub"] for item in yield_records)
    cost = sum(item["cost_rub"] for item in yield_records)
    return {
        "total_revenue_rub": revenue,
        "total_cost_rub": cost,
        "margin_pct": economic_margin_pct(revenue, cost),
    }


@app.get("/analytics/telemetry/capacity-plan")
async def telemetry_capacity(sensor_count: int = 10000, regions: int = 10) -> dict[str, Any]:
    return telemetry_realtime_plan(sensor_count, regions)


@app.get("/analytics/kpi")
async def kpi(actor_role: Role = Role.MANAGER) -> dict[str, Any]:
    _assert_permission(actor_role, "analytics:read")
    predicted = [item["predicted_t_ha"] for item in yield_records]
    actual = [item["actual_t_ha"] for item in yield_records]
    avg_latency = round(mean(sensor_latencies), 3) if sensor_latencies else 0.0
    return {
        "yield_mape_pct": yield_mape(predicted, actual),
        "target_yield_mape_pct": settings.yield_mape_target,
        "avg_sensor_latency_seconds": avg_latency,
        "target_sensor_latency_seconds": settings.sensor_latency_target_seconds,
        "sensor_capacity_target": settings.sensor_capacity_target,
    }


@app.get("/dashboards/agronomist")
async def agronomist_dashboard() -> dict[str, Any]:
    top_fields = sorted(yield_records, key=lambda row: row["actual_t_ha"], reverse=True)[:5]
    return {
        "kpi": await kpi(Role.MANAGER),
        "top_fields": top_fields,
        "yearly": yearly_yield_summary(yield_records),
    }
