# Architecture

## Context

AgriSense supports precision agriculture across field monitoring, irrigation management, fertilization planning, and yield analytics.

## Service map

- `api-gateway`: central entry, workflow orchestration, dashboard aggregation
- `iot-service`: sensor ingestion, weather feed, drone scans, realtime plan for telemetry workers
- `field-service`: field geometry and zoning, treatment history, map cache layer
- `analysis-service`: threshold checks, irrigation and fertilizer recommendations, yield forecast, crop rotation
- `planning-service`: agrotechnical calendar, task assignment, workload visibility
- `analytics-service`: annual yield comparison, economics, KPI tracking against SLA targets
- `integration-service`: GPS machinery sync, weather integration, agrochemical supplier exchange, offline map packages
- `notification-service`: alerts to agronomists and managers

## Infrastructure

- PostgreSQL for metadata and planning entities
- TimescaleDB for telemetry time series workloads
- PostGIS for geospatial workloads and map data
- RabbitMQ for workflow events and service messaging
- MQTT broker for sensor-side connectivity
- Redis for cache and short-lived state

## Key workflows

1. `process-sensor`: ingest telemetry -> threshold check -> alert -> update field stats
2. `plan-field-work`: compute fertilizer and irrigation -> generate yield forecast -> create planned task
3. Dashboard aggregation: field state, IoT pulse, planning status, yearly analytics, economics

## Scalability notes

- Realtime telemetry planner supports sizing worker pools for 10k+ sensors
- Field map cache reduces repeated tile computation
- Analytics and operational services are isolated for predictable response time
- Integrations are isolated behind `integration-service`
