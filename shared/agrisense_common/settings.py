from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "agrisense-service"
    service_port: int = 8400
    environment: str = "dev"

    postgres_dsn: str = "postgresql+psycopg://agrisense:agrisense@postgres:5432/agrisense"
    timescale_dsn: str = "postgresql+psycopg://agrisense:agrisense@timescaledb:5432/agrisense"
    postgis_dsn: str = "postgresql+psycopg://agrisense:agrisense@postgis:5432/agrisense"

    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"
    mqtt_broker_url: str = "mqtt://mosquitto:1883"

    weather_provider_url: str = "https://api.open-meteo.com"
    gps_provider_url: str = "https://gps.agri.local"
    agrochem_provider_url: str = "https://supplier.agri.local"

    jwt_secret: str = "agrisense-dev-secret"
    encryption_key: str = "agrisense-dev-encryption-key"

    yield_mape_target: float = 12.0
    sensor_latency_target_seconds: float = 10.0
    sensor_capacity_target: int = 10000

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
