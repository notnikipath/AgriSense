# Deployment

## Requirements

- Docker
- Docker Compose
- Python 3.11 for local lint and tests

## Start

```bash
cd d:\Шарага\Кинжа3\Task_14_AgriSense
docker compose up --build -d
```

## Stop

```bash
docker compose down
```

## Validate

```bash
python -m ruff check .
python -m pytest -q
docker compose config
```

## Ports

- `8580` gateway
- `5184` frontend
- `8401-8407` backend services
- `55445` PostgreSQL
- `55446` TimescaleDB
- `55447` PostGIS
- `6384` Redis
- `5673` RabbitMQ
- `1884` MQTT
