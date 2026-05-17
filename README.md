# AgriSense

AgriSense is a microservice platform for digital farm management: sensor telemetry, field maps, irrigation and fertilization recommendations, yield forecasting, work planning, and operational analytics.

## Modules

- `api-gateway` - orchestration, auth, service health, workflows, unified dashboard
- `iot-service` - IoT sensors, weather ingestion, drone scan ingestion, realtime telemetry plans
- `field-service` - field boundaries, soil zoning, treatment history, map cache
- `analysis-service` - irrigation and fertilizer recommendations, yield forecast, thresholds, crop rotation optimization
- `planning-service` - agrotechnical calendar, resource assignment, workload
- `analytics-service` - yearly yield comparisons, economic efficiency, KPI dashboard
- `integration-service` - GPS sync, weather integration, agrochem exchange, offline mobile map packages
- `notification-service` - agronomist alerts and notification history
- `frontend` - agronomist and manager dashboard

## Mandatory functionality covered

- Supported crops: wheat, corn, vegetables, fruit trees, technical crops
- IoT data ingestion: soil moisture, temperature, light
- Weather station and drone scan streams
- Vector-like field boundaries and soil zones
- Irrigation and fertilizer recommendations
- Yield forecast with MAPE tracking
- Calendar planning with machinery and personnel assignment
- Yield comparison and economics analytics
- GPS and supplier integrations

## Optional improvements implemented (6)

1. Automatic irrigation control from sensor data (A2)
2. Crop rotation optimization (A4)
3. Weather service integration (B1)
4. Realtime processing plan for large telemetry streams (C1)
5. Map caching for field visualization (C2)
6. Mobile offline map package endpoint (D1)

## Quality metrics

- Yield forecast quality target: `MAPE < 12%`
- Sensor response target: `< 10 sec`
- Sensor capacity target: `10,000`

## Tech stack

- Backend: Python + FastAPI
- Data layer: PostgreSQL, TimescaleDB, PostGIS
- Queue and stream protocol: RabbitMQ, MQTT
- Analytics stack: Pandas and Scikit-learn and Prophet (ready for extension)
- Frontend: React + Vite

## Local run

```bash
cd d:\Шарага\Кинжа3\Task_14_AgriSense
docker compose up --build -d
```

## Useful URLs

- Frontend: `http://localhost:5184`
- Gateway health: `http://localhost:8580/health`
- Services health: `http://localhost:8580/services/health`
- Swagger: `http://localhost:8580/docs`

## Validation

```bash
python -m ruff check .
python -m pytest -q
docker compose config
```

## Demo workflow

```bash
python scripts/demo_pipeline.py
```

## Sample data

Generate synthetic telemetry for 12k events:

```bash
python scripts/generate_sample_data.py
```

Result file: `data/samples/agri_events.json`
