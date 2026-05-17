from __future__ import annotations

from datetime import UTC, datetime
from statistics import mean

from .schemas import CropType, SoilType


def yield_mape(predicted_t_ha: list[float], actual_t_ha: list[float]) -> float:
    if not predicted_t_ha or not actual_t_ha or len(predicted_t_ha) != len(actual_t_ha):
        return 0.0
    errors: list[float] = []
    for predicted, actual in zip(predicted_t_ha, actual_t_ha, strict=True):
        if actual <= 0:
            continue
        errors.append(abs((actual - predicted) / actual))
    if not errors:
        return 0.0
    return round(sum(errors) / len(errors) * 100, 2)


def sensor_latency_seconds(measured_at: datetime, now: datetime | None = None) -> float:
    current = now or datetime.now(UTC)
    return round(max((current - measured_at).total_seconds(), 0.0), 3)


def irrigation_need_liters_per_ha(moisture_pct: float, temperature_c: float, crop_type: CropType) -> float:
    target_by_crop = {
        CropType.WHEAT: 38.0,
        CropType.CORN: 42.0,
        CropType.VEGETABLES: 50.0,
        CropType.FRUIT_TREES: 45.0,
        CropType.TECHNICAL: 40.0,
    }
    target_moisture = target_by_crop[crop_type]
    deficit = max(target_moisture - moisture_pct, 0.0)
    heat_factor = 1 + max(temperature_c - 25, 0) * 0.02
    return round(deficit * 110 * heat_factor, 2)


def fertilizer_need_kg_ha(crop_type: CropType, soil_type: SoilType, target_yield_t_ha: float, ndvi: float) -> float:
    crop_factor = {
        CropType.WHEAT: 1.0,
        CropType.CORN: 1.15,
        CropType.VEGETABLES: 1.3,
        CropType.FRUIT_TREES: 0.9,
        CropType.TECHNICAL: 1.08,
    }[crop_type]
    soil_factor = {
        SoilType.CHERNOZEM: 0.82,
        SoilType.LOAM: 1.0,
        SoilType.SANDY: 1.2,
        SoilType.CLAY: 1.12,
        SoilType.PEATY: 0.92,
    }[soil_type]
    vegetation_factor = max(0.55, 1.25 - ndvi)
    return round(target_yield_t_ha * 42 * crop_factor * soil_factor * vegetation_factor, 2)


def economic_margin_pct(revenue_rub: float, cost_rub: float) -> float:
    if revenue_rub <= 0:
        return 0.0
    return round((revenue_rub - cost_rub) / revenue_rub * 100, 2)


def telemetry_realtime_plan(sensor_count: int, regions: int) -> dict[str, int]:
    workers = min(64, max(2, regions * 3, sensor_count // 220))
    batch_size = max(100, sensor_count // max(workers, 1)) if sensor_count else 100
    queue_partitions = max(4, workers // 2)
    return {
        "workers": workers,
        "batch_size": batch_size,
        "queue_partitions": queue_partitions,
        "sensor_count": sensor_count,
    }


def map_cache_tiles_estimate(area_ha: float, zoom: int = 16) -> int:
    density = max(8, min(30, zoom))
    return int(max(area_ha, 0.5) * density)


def offline_pack_size_mb(area_ha: float, zoom: int = 16) -> float:
    tiles = map_cache_tiles_estimate(area_ha, zoom)
    return round(tiles * 0.085, 2)


def yearly_yield_summary(records: list[dict]) -> list[dict]:
    grouped: dict[int, dict[str, list[float]]] = {}
    for row in records:
        year = int(row["year"])
        bucket = grouped.setdefault(year, {"predicted": [], "actual": []})
        bucket["predicted"].append(float(row["predicted_t_ha"]))
        bucket["actual"].append(float(row["actual_t_ha"]))
    result = []
    for year, values in sorted(grouped.items()):
        predicted = round(mean(values["predicted"]), 2)
        actual = round(mean(values["actual"]), 2)
        result.append(
            {
                "year": year,
                "predicted_t_ha": predicted,
                "actual_t_ha": actual,
                "delta_t_ha": round(actual - predicted, 2),
            }
        )
    return result
