# API Overview

## Gateway

- `POST /auth/token`
- `POST /auth/verify`
- `GET /services/health`
- `POST /workflow/process-sensor`
- `POST /workflow/plan-field-work`
- `GET /dashboard/{field_id}`

## IoT service

- `GET /sensors`
- `POST /sensors/register`
- `POST /telemetry/ingest`
- `POST /weather/ingest`
- `POST /drone/ingest`
- `GET /fields/{field_id}/snapshot`
- `GET /processing/realtime-plan`

## Field service

- `GET /fields`
- `GET /fields/{field_id}`
- `POST /fields`
- `POST /fields/{field_id}/treatments`
- `GET /fields/{field_id}/history`
- `GET /maps/cache/tiles`

## Analysis service

- `POST /analysis/sensor/check-threshold`
- `POST /analysis/fields/{field_id}/stats/update`
- `POST /analysis/irrigation`
- `POST /analysis/fertilizer`
- `POST /analysis/yield-forecast`
- `POST /analysis/crop-rotation/optimize`
- `GET /analysis/kpi`

## Planning service

- `GET /resources`
- `POST /tasks`
- `GET /tasks`
- `POST /tasks/{task_id}/assign`
- `POST /tasks/{task_id}/status`
- `GET /calendar`

## Analytics service

- `POST /analytics/ingest/yield`
- `POST /analytics/ingest/sensor-latency`
- `GET /analytics/yield/comparison`
- `GET /analytics/economics`
- `GET /analytics/kpi`
- `GET /analytics/telemetry/capacity-plan`

## Integration service

- `POST /integrations/sync`
- `POST /integrations/gps/sync`
- `POST /integrations/agrochem/sync`
- `POST /integrations/weather/fetch`
- `GET /integrations/weather/latest/{field_id}`
- `GET /mobile/offline-maps/{field_id}`

## Notification service

- `POST /notify/send`
- `POST /notify/agronomist-alert`
- `GET /notify/history`
