from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from shared.agrisense_common import NotificationChannel, NotificationPayload, Role, Settings, Severity, has_permission

settings = Settings(service_name="notification-service", service_port=8407)
app = FastAPI(title="AgriSense Notification Service", version="1.0.0")

messages: list[dict[str, Any]] = []


class NotificationRequest(BaseModel):
    channel: NotificationChannel
    recipient: str
    subject: str
    body: str
    severity: Severity = Severity.INFO
    actor_role: Role


class AgronomistAlertRequest(BaseModel):
    field_id: str
    sensor_id: str
    severity: Severity
    message: str
    recipient: str = "agronomist@agrisense.local"
    actor_role: Role


NotificationRequest.model_rebuild()
AgronomistAlertRequest.model_rebuild()


def _assert_permission(role: Role, action: str) -> None:
    if not has_permission(role, action):
        raise HTTPException(status_code=403, detail=f"Role {role.value} cannot {action}")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.post("/notify/send")
async def send_notification(request: NotificationRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "notification:send")
    payload = NotificationPayload(
        channel=request.channel,
        recipient=request.recipient,
        subject=request.subject,
        body=request.body,
        severity=request.severity,
    ).model_dump(mode="json")
    payload["status"] = "queued"
    messages.append(payload)
    return payload


@app.post("/notify/agronomist-alert")
async def notify_agronomist(request: AgronomistAlertRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "notification:send")
    payload = NotificationPayload(
        channel=NotificationChannel.PUSH,
        recipient=request.recipient,
        subject=f"Field {request.field_id}: {request.severity.value} alert",
        body=f"Sensor {request.sensor_id}: {request.message}",
        severity=request.severity,
    ).model_dump(mode="json")
    payload["status"] = "queued"
    messages.append(payload)
    return payload


@app.get("/notify/history")
async def history() -> dict[str, Any]:
    return {"items": messages, "count": len(messages)}
