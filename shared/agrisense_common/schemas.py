from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class CropType(str, Enum):
    WHEAT = "wheat"
    CORN = "corn"
    VEGETABLES = "vegetables"
    FRUIT_TREES = "fruit_trees"
    TECHNICAL = "technical"


class SensorType(str, Enum):
    SOIL_MOISTURE = "soil_moisture"
    TEMPERATURE_C = "temperature_c"
    LIGHT_LUX = "light_lux"


class SoilType(str, Enum):
    CHERNOZEM = "chernozem"
    LOAM = "loam"
    SANDY = "sandy"
    CLAY = "clay"
    PEATY = "peaty"


class WorkType(str, Enum):
    IRRIGATION = "irrigation"
    FERTILIZATION = "fertilization"
    SOWING = "sowing"
    SCOUTING = "scouting"
    SPRAYING = "spraying"
    HARVEST = "harvest"


class TaskStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class Role(str, Enum):
    AGRONOMIST = "agronomist"
    OPERATOR = "operator"
    ANALYST = "analyst"
    MANAGER = "manager"
    ADMIN = "admin"


class GeoPoint(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class FieldZone(BaseModel):
    zone_id: str
    soil_type: SoilType
    area_ha: float = Field(gt=0)
    ph: float = Field(default=6.5, ge=3.5, le=9.5)
    organic_matter_pct: float = Field(default=2.5, ge=0, le=20)


class TreatmentRecord(BaseModel):
    event_id: str
    field_id: str
    work_type: WorkType
    date: datetime = Field(default_factory=lambda: datetime.now(UTC))
    fertilizer_kg_ha: float = Field(default=0, ge=0)
    irrigation_mm: float = Field(default=0, ge=0)
    note: str = ""


class FieldCreateRequest(BaseModel):
    name: str
    region: str
    crop_type: CropType
    area_ha: float = Field(gt=0)
    boundary: list[GeoPoint] = Field(min_length=3)
    zones: list[FieldZone] = Field(default_factory=list)
    actor_id: str
    actor_role: Role


class FieldProfile(BaseModel):
    field_id: str
    name: str
    region: str
    crop_type: CropType
    area_ha: float = Field(gt=0)
    boundary: list[GeoPoint] = Field(default_factory=list)
    zones: list[FieldZone] = Field(default_factory=list)
    treatment_history: list[TreatmentRecord] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SensorDevice(BaseModel):
    sensor_id: str
    field_id: str
    sensor_type: SensorType
    threshold_low: float | None = None
    threshold_high: float | None = None
    installed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SensorRegisterRequest(BaseModel):
    field_id: str
    sensor_type: SensorType
    threshold_low: float | None = None
    threshold_high: float | None = None
    actor_id: str
    actor_role: Role


class SensorReading(BaseModel):
    sensor_id: str
    field_id: str
    sensor_type: SensorType
    value: float
    unit: str
    timestamp: datetime


class SensorReadingBatch(BaseModel):
    readings: list[SensorReading] = Field(default_factory=list)
    actor_role: Role


class WeatherSnapshot(BaseModel):
    field_id: str
    timestamp: datetime
    temperature_c: float
    humidity_pct: float = Field(ge=0, le=100)
    rainfall_mm: float = Field(ge=0)
    wind_mps: float = Field(ge=0)


class DroneScan(BaseModel):
    field_id: str
    scan_id: str
    timestamp: datetime
    ndvi_mean: float = Field(ge=0, le=1)
    moisture_index: float = Field(ge=0, le=1)
    image_url: str | None = None


class IrrigationRecommendation(BaseModel):
    field_id: str
    liters_per_ha: float = Field(ge=0)
    reason: str
    auto_apply: bool = False
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FertilizerRecommendation(BaseModel):
    field_id: str
    npk_formula: str
    dosage_kg_ha: float = Field(ge=0)
    rationale: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class YieldForecast(BaseModel):
    field_id: str
    season: str
    predicted_t_ha: float = Field(ge=0)
    confidence_pct: float = Field(ge=0, le=100)
    model_name: str = "Scikit-Learn + Prophet"
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FieldStats(BaseModel):
    field_id: str
    avg_moisture_pct: float = Field(ge=0)
    avg_temperature_c: float
    avg_light_lux: float = Field(ge=0)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SensorThresholdCheckRequest(BaseModel):
    sensor_id: str
    field_id: str
    sensor_type: SensorType
    value: float


class ThresholdAlert(BaseModel):
    alert_id: str
    field_id: str
    sensor_id: str
    severity: Severity
    message: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FieldStatsUpdateRequest(BaseModel):
    sensor_id: str
    field_id: str
    sensor_type: SensorType
    value: float


class TaskCreateRequest(BaseModel):
    field_id: str
    work_type: WorkType
    planned_start: datetime
    planned_end: datetime
    assignee: str | None = None
    machinery: str | None = None
    actor_id: str
    actor_role: Role


class WorkTask(BaseModel):
    task_id: str
    field_id: str
    work_type: WorkType
    planned_start: datetime
    planned_end: datetime
    assignee: str | None = None
    machinery: str | None = None
    status: TaskStatus = TaskStatus.PLANNED
    notes: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TaskAssignmentRequest(BaseModel):
    assignee: str
    machinery: str
    actor_id: str
    actor_role: Role


class TaskStatusUpdateRequest(BaseModel):
    status: TaskStatus
    notes: str = ""
    actor_id: str
    actor_role: Role


class IntegrationSyncRequest(BaseModel):
    system_name: str
    payload: dict[str, Any] = Field(default_factory=dict)
    actor_id: str
    actor_role: Role


class IntegrationSyncResult(BaseModel):
    sync_id: str
    system_name: str
    status: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class NotificationPayload(BaseModel):
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    severity: Severity = Severity.INFO
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SensorWorkflowRequest(BaseModel):
    sensor_id: str
    field_id: str
    sensor_type: SensorType
    value: float
    unit: str
    timestamp: datetime


class SensorWorkflowResult(BaseModel):
    reading: dict[str, Any]
    alert: dict[str, Any] | None
    field_stats: dict[str, Any]
    processed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class YieldEconomicsRecord(BaseModel):
    field_id: str
    year: int
    predicted_t_ha: float = Field(ge=0)
    actual_t_ha: float = Field(ge=0)
    revenue_rub: float = Field(ge=0)
    cost_rub: float = Field(ge=0)


class AuditEvent(BaseModel):
    event_id: str
    actor_id: str
    actor_role: Role | str
    action: str
    object_type: str
    object_id: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
