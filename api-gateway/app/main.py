from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.agrisense_common import Role, SensorType, SensorWorkflowResult, Settings, sign_token, verify_token


class GatewaySettings(BaseSettings):
    service_name: str = "api-gateway"
    service_port: int = 8400

    iot_service_url: str = "http://iot-service:8401"
    field_service_url: str = "http://field-service:8402"
    analysis_service_url: str = "http://analysis-service:8403"
    planning_service_url: str = "http://planning-service:8404"
    analytics_service_url: str = "http://analytics-service:8405"
    integration_service_url: str = "http://integration-service:8406"
    notification_service_url: str = "http://notification-service:8407"

    jwt_secret: str = Settings().jwt_secret
    token_exp_minutes: int = 240

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = GatewaySettings()
app = FastAPI(title="AgriSense API Gateway", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5177",
        "http://127.0.0.1:5177",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
        "http://localhost:5184",
        "http://127.0.0.1:5184",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AuthRequest(BaseModel):
    user_id: str
    role: Role
    language: str = Field(default="ru", pattern="^(ru|en)$")


class SensorWorkflowRequest(BaseModel):
    sensor_id: str
    field_id: str
    sensor_type: SensorType
    value: float
    unit: str = "%"
    timestamp: datetime


class FieldWorkPlanWorkflowRequest(BaseModel):
    field_id: str
    crop_type: str
    soil_type: str
    target_yield_t_ha: float = Field(gt=0)
    ndvi: float = Field(ge=0, le=1)
    moisture_pct: float = Field(ge=0, le=100)
    temperature_c: float
    rainfall_mm: float = Field(ge=0)
    actor_id: str
    actor_role: Role


AuthRequest.model_rebuild()
SensorWorkflowRequest.model_rebuild()
FieldWorkPlanWorkflowRequest.model_rebuild()


async def _post_json(client: httpx.AsyncClient, url: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = await client.post(url, json=payload)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = await client.get(url, params=params)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


def _service_urls() -> dict[str, str]:
    return {
        "iot": settings.iot_service_url,
        "field": settings.field_service_url,
        "analysis": settings.analysis_service_url,
        "planning": settings.planning_service_url,
        "analytics": settings.analytics_service_url,
        "integration": settings.integration_service_url,
        "notification": settings.notification_service_url,
    }


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/auth/token")
async def issue_token(request: AuthRequest) -> dict[str, str]:
    token = sign_token(
        {"sub": request.user_id, "role": request.role.value, "language": request.language},
        settings.jwt_secret,
        exp_minutes=settings.token_exp_minutes,
    )
    return {"access_token": token, "token_type": "Bearer"}


@app.post("/auth/verify")
async def verify_auth(token: str) -> dict[str, Any]:
    payload = verify_token(token, settings.jwt_secret)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    return payload


@app.get("/services/health")
async def service_health() -> dict[str, Any]:
    statuses: dict[str, Any] = {}
    async with httpx.AsyncClient(timeout=10.0) as client:
        for name, base_url in _service_urls().items():
            try:
                statuses[name] = await _get_json(client, f"{base_url}/health")
            except HTTPException as exc:
                statuses[name] = {"status": "error", "detail": exc.detail}
            except httpx.HTTPError as exc:
                statuses[name] = {"status": "error", "detail": str(exc)}
    return statuses


@app.post("/workflow/process-sensor")
async def process_sensor_workflow(request: SensorWorkflowRequest) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=25.0) as client:
        reading_result = await _post_json(
            client,
            f"{settings.iot_service_url}/telemetry/ingest",
            {
                "readings": [
                    {
                        "sensor_id": request.sensor_id,
                        "field_id": request.field_id,
                        "sensor_type": request.sensor_type.value,
                        "value": request.value,
                        "unit": request.unit,
                        "timestamp": request.timestamp.isoformat(),
                    }
                ],
                "actor_role": Role.OPERATOR.value,
            },
        )

        alert_result = await _post_json(
            client,
            f"{settings.analysis_service_url}/analysis/sensor/check-threshold",
            {
                "sensor_id": request.sensor_id,
                "field_id": request.field_id,
                "sensor_type": request.sensor_type.value,
                "value": request.value,
            },
        )
        alert = alert_result.get("alert")

        if alert:
            await _post_json(
                client,
                f"{settings.notification_service_url}/notify/agronomist-alert",
                {
                    "field_id": request.field_id,
                    "sensor_id": request.sensor_id,
                    "severity": alert["severity"],
                    "message": alert["message"],
                    "actor_role": Role.AGRONOMIST.value,
                },
            )

        field_stats = await _post_json(
            client,
            f"{settings.analysis_service_url}/analysis/fields/{request.field_id}/stats/update",
            {
                "sensor_id": request.sensor_id,
                "field_id": request.field_id,
                "sensor_type": request.sensor_type.value,
                "value": request.value,
            },
        )

    result = SensorWorkflowResult(
        reading=reading_result,
        alert=alert,
        field_stats=field_stats,
    )
    return result.model_dump(mode="json")


@app.post("/workflow/plan-field-work")
async def plan_field_workflow(request: FieldWorkPlanWorkflowRequest) -> dict[str, Any]:
    now = datetime.now(UTC)
    async with httpx.AsyncClient(timeout=30.0) as client:
        fertilizer = await _post_json(
            client,
            f"{settings.analysis_service_url}/analysis/fertilizer",
            {
                "field_id": request.field_id,
                "crop_type": request.crop_type,
                "soil_type": request.soil_type,
                "target_yield_t_ha": request.target_yield_t_ha,
                "ndvi": request.ndvi,
            },
        )
        irrigation = await _post_json(
            client,
            f"{settings.analysis_service_url}/analysis/irrigation",
            {
                "field_id": request.field_id,
                "crop_type": request.crop_type,
                "avg_moisture_pct": request.moisture_pct,
                "temperature_c": request.temperature_c,
                "rainfall_mm": request.rainfall_mm,
                "auto_mode": True,
            },
        )
        forecast = await _post_json(
            client,
            f"{settings.analysis_service_url}/analysis/yield-forecast",
            {
                "field_id": request.field_id,
                "season": f"{now.year}",
                "crop_type": request.crop_type,
                "avg_moisture_pct": request.moisture_pct,
                "avg_temp_c": request.temperature_c,
                "light_lux": 43000,
                "rainfall_mm": request.rainfall_mm,
                "ndvi": request.ndvi,
            },
        )
        task = await _post_json(
            client,
            f"{settings.planning_service_url}/tasks",
            {
                "field_id": request.field_id,
                "work_type": "fertilization",
                "planned_start": (now + timedelta(hours=2)).isoformat(),
                "planned_end": (now + timedelta(hours=7)).isoformat(),
                "assignee": "agronomist.ivanov",
                "machinery": "Tractor-09",
                "actor_id": request.actor_id,
                "actor_role": request.actor_role.value,
            },
        )
    return {
        "fertilizer": fertilizer,
        "irrigation": irrigation,
        "forecast": forecast,
        "planned_task": task,
    }


@app.get("/dashboard/{field_id}")
async def dashboard(field_id: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        field = await _get_json(client, f"{settings.field_service_url}/fields/{field_id}")
        field_history = await _get_json(client, f"{settings.field_service_url}/fields/{field_id}/history")
        iot_snapshot = await _get_json(client, f"{settings.iot_service_url}/fields/{field_id}/snapshot")
        iot_alerts = await _get_json(client, f"{settings.iot_service_url}/alerts")
        stats = await _get_json(client, f"{settings.analysis_service_url}/analysis/field-stats/{field_id}")
        analysis_kpi = await _get_json(client, f"{settings.analysis_service_url}/analysis/kpi")
        tasks = await _get_json(client, f"{settings.planning_service_url}/tasks", {"field_id": field_id})
        workload = await _get_json(client, f"{settings.planning_service_url}/workload")
        analytics_kpi = await _get_json(
            client,
            f"{settings.analytics_service_url}/analytics/kpi",
            {"actor_role": Role.MANAGER.value},
        )
        yearly = await _get_json(client, f"{settings.analytics_service_url}/analytics/yield/comparison")
        economics = await _get_json(client, f"{settings.analytics_service_url}/analytics/economics")
        weather = await _get_json(client, f"{settings.integration_service_url}/integrations/weather/latest/{field_id}")
        integrations = await _get_json(client, f"{settings.integration_service_url}/integrations/history")
        notifications = await _get_json(client, f"{settings.notification_service_url}/notify/history")

    return {
        "field": field,
        "field_history": field_history,
        "iot_snapshot": iot_snapshot,
        "iot_alerts": iot_alerts,
        "analysis_stats": stats,
        "analysis_kpi": analysis_kpi,
        "tasks": tasks,
        "workload": workload,
        "analytics_kpi": analytics_kpi,
        "yearly_yield": yearly,
        "economics": economics,
        "weather": weather,
        "integrations": integrations,
        "notifications": notifications,
    }
