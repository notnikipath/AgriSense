from __future__ import annotations

from .schemas import CropType, SensorType, Severity, SoilType


def forecast_yield_t_ha(
    crop_type: CropType,
    avg_moisture_pct: float,
    avg_temp_c: float,
    light_lux: float,
    rainfall_mm: float,
    ndvi: float,
) -> float:
    crop_base = {
        CropType.WHEAT: 5.1,
        CropType.CORN: 7.8,
        CropType.VEGETABLES: 24.0,
        CropType.FRUIT_TREES: 16.5,
        CropType.TECHNICAL: 4.8,
    }[crop_type]
    moisture_score = max(0.55, min(1.15, 0.75 + avg_moisture_pct / 100))
    temp_score = max(0.7, 1 - abs(avg_temp_c - 23.0) * 0.015)
    light_score = max(0.7, min(1.2, light_lux / 30000))
    rain_score = max(0.75, min(1.15, 0.9 + rainfall_mm / 180))
    ndvi_score = max(0.6, min(1.2, ndvi + 0.35))
    predicted = crop_base * moisture_score * temp_score * light_score * rain_score * ndvi_score
    return round(max(predicted, 0.2), 2)


def check_sensor_threshold(sensor_type: SensorType, value: float) -> dict[str, str] | None:
    bounds = {
        SensorType.SOIL_MOISTURE: (24.0, 62.0),
        SensorType.TEMPERATURE_C: (7.0, 38.0),
        SensorType.LIGHT_LUX: (5000.0, 95000.0),
    }
    low, high = bounds[sensor_type]
    if value < low:
        severity = Severity.CRITICAL if sensor_type == SensorType.SOIL_MOISTURE else Severity.WARNING
        return {
            "severity": severity.value,
            "message": f"{sensor_type.value} below safe bound {low}",
        }
    if value > high:
        severity = Severity.CRITICAL if sensor_type == SensorType.TEMPERATURE_C else Severity.WARNING
        return {
            "severity": severity.value,
            "message": f"{sensor_type.value} above safe bound {high}",
        }
    return None


def recommend_irrigation_schedule(
    moisture_pct: float,
    temperature_c: float,
    rainfall_mm: float,
    crop_type: CropType,
) -> dict[str, float | str]:
    crop_interval_days = {
        CropType.WHEAT: 6,
        CropType.CORN: 5,
        CropType.VEGETABLES: 3,
        CropType.FRUIT_TREES: 4,
        CropType.TECHNICAL: 6,
    }[crop_type]
    stress = max(0.0, 35 - moisture_pct) + max(0.0, temperature_c - 30) * 1.8 - rainfall_mm * 0.8
    next_in_days = max(1, round(crop_interval_days - stress / 15))
    priority = "high" if stress >= 18 else "normal"
    return {
        "next_in_days": float(next_in_days),
        "stress_index": round(stress, 2),
        "priority": priority,
    }


def recommend_fertilizer_formula(crop_type: CropType, soil_type: SoilType, ndvi: float) -> tuple[str, str]:
    if crop_type == CropType.VEGETABLES:
        formula = "N20-P20-K20"
    elif crop_type == CropType.CORN:
        formula = "N24-P12-K12"
    elif crop_type == CropType.WHEAT:
        formula = "N16-P16-K16"
    elif crop_type == CropType.FRUIT_TREES:
        formula = "N12-P18-K24"
    else:
        formula = "N18-P12-K18"

    if soil_type in {SoilType.SANDY, SoilType.CLAY}:
        formula = f"{formula}+Mg"

    focus = "nitrogen" if ndvi < 0.55 else "balanced"
    return formula, focus


def optimize_crop_rotation(current_crop: CropType, soil_type: SoilType, horizon_years: int = 3) -> dict[str, object]:
    options = {
        CropType.WHEAT: [CropType.TECHNICAL, CropType.CORN, CropType.VEGETABLES],
        CropType.CORN: [CropType.WHEAT, CropType.TECHNICAL, CropType.VEGETABLES],
        CropType.VEGETABLES: [CropType.WHEAT, CropType.TECHNICAL, CropType.CORN],
        CropType.FRUIT_TREES: [CropType.FRUIT_TREES, CropType.VEGETABLES, CropType.WHEAT],
        CropType.TECHNICAL: [CropType.WHEAT, CropType.CORN, CropType.VEGETABLES],
    }
    sequence = options[current_crop][: max(horizon_years, 1)]
    soil_bonus = 8 if soil_type == SoilType.CHERNOZEM else 0
    diversity = len({item for item in sequence})
    score = round(70 + diversity * 6 + soil_bonus - (4 if current_crop == CropType.FRUIT_TREES else 0), 2)
    return {
        "sequence": [crop.value for crop in sequence],
        "score": score,
    }


def detect_plant_stress(ndvi: float, moisture_pct: float, temperature_c: float) -> dict[str, str]:
    if ndvi < 0.42 or moisture_pct < 22:
        return {"level": Severity.CRITICAL.value, "message": "Potential drought stress"}
    if temperature_c > 36:
        return {"level": Severity.WARNING.value, "message": "Heat stress risk"}
    return {"level": Severity.INFO.value, "message": "Vegetation state is stable"}
