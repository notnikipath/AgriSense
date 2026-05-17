from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException

from shared.agrisense_common import (
    Role,
    Settings,
    TaskAssignmentRequest,
    TaskCreateRequest,
    TaskStatus,
    TaskStatusUpdateRequest,
    WorkTask,
    build_audit_event,
    has_permission,
)

settings = Settings(service_name="planning-service", service_port=8404)
app = FastAPI(title="AgriSense Planning Service", version="1.0.0")

resources = {
    "machinery": ["Pivot-01", "Pivot-02", "Sprayer-11", "Tractor-09", "Combine-07"],
    "personnel": ["agronomist.ivanov", "operator.smirnov", "brigade.north", "brigade.south"],
}

work_tasks: dict[str, WorkTask] = {
    "TASK-DEMO-1": WorkTask(
        task_id="TASK-DEMO-1",
        field_id="FIELD-DEMO-1",
        work_type="scouting",
        planned_start=datetime.now(UTC),
        planned_end=datetime.now(UTC) + timedelta(hours=4),
        assignee="agronomist.ivanov",
        machinery="Tractor-09",
        status=TaskStatus.PLANNED,
        notes="Weekly field walk",
    )
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
            object_type="planning",
            object_id=object_id,
            details=details or {},
        ).model_dump(mode="json")
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/resources")
async def list_resources() -> dict[str, Any]:
    return resources


@app.post("/tasks")
async def create_task(request: TaskCreateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "planning:write")
    task_id = f"TASK-{uuid4().hex[:10].upper()}"
    task = WorkTask(
        task_id=task_id,
        field_id=request.field_id,
        work_type=request.work_type,
        planned_start=request.planned_start,
        planned_end=request.planned_end,
        assignee=request.assignee,
        machinery=request.machinery,
    )
    work_tasks[task_id] = task
    _audit(request.actor_id, request.actor_role, "planning.task.create", task_id, {"field_id": request.field_id})
    return task.model_dump(mode="json")


@app.get("/tasks")
async def list_tasks(field_id: str | None = None, status: TaskStatus | None = None) -> dict[str, Any]:
    items = []
    for task in work_tasks.values():
        if field_id and task.field_id != field_id:
            continue
        if status and task.status != status:
            continue
        items.append(task.model_dump(mode="json"))
    items.sort(key=lambda row: row["planned_start"])
    return {"items": items, "count": len(items)}


@app.post("/tasks/{task_id}/assign")
async def assign_task(task_id: str, request: TaskAssignmentRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "planning:write")
    task = work_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.assignee = request.assignee
    task.machinery = request.machinery
    _audit(request.actor_id, request.actor_role, "planning.task.assign", task_id)
    return task.model_dump(mode="json")


@app.post("/tasks/{task_id}/status")
async def update_task_status(task_id: str, request: TaskStatusUpdateRequest) -> dict[str, Any]:
    _assert_permission(request.actor_role, "planning:write")
    task = work_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    task.status = request.status
    if request.notes:
        task.notes = request.notes
    _audit(request.actor_id, request.actor_role, "planning.task.status", task_id, {"status": request.status.value})
    return task.model_dump(mode="json")


@app.get("/calendar")
async def calendar(date_from: datetime | None = None, date_to: datetime | None = None) -> dict[str, Any]:
    items = []
    for task in work_tasks.values():
        if date_from and task.planned_end < date_from:
            continue
        if date_to and task.planned_start > date_to:
            continue
        items.append(task.model_dump(mode="json"))
    items.sort(key=lambda row: row["planned_start"])
    return {"items": items, "count": len(items)}


@app.get("/workload")
async def workload() -> dict[str, Any]:
    by_assignee: dict[str, int] = {}
    by_machinery: dict[str, int] = {}
    for task in work_tasks.values():
        if task.assignee:
            by_assignee[task.assignee] = by_assignee.get(task.assignee, 0) + 1
        if task.machinery:
            by_machinery[task.machinery] = by_machinery.get(task.machinery, 0) + 1
    return {"assignees": by_assignee, "machinery": by_machinery}


@app.get("/audit")
async def get_audit(limit: int = 100, actor_role: Role = Role.ADMIN) -> dict[str, Any]:
    _assert_permission(actor_role, "audit:read")
    return {"items": audit_log[-limit:]}
