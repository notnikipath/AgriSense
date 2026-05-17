from shared.agrisense_common import check_sensor_threshold, forecast_yield_t_ha, optimize_crop_rotation
from shared.agrisense_common.schemas import CropType, SensorType, SoilType


def test_forecast_yield_positive() -> None:
    value = forecast_yield_t_ha(
        CropType.WHEAT,
        avg_moisture_pct=34,
        avg_temp_c=22,
        light_lux=42000,
        rainfall_mm=28,
        ndvi=0.63,
    )
    assert value > 0
    assert value < 20



def test_sensor_threshold_detects_dry_soil() -> None:
    finding = check_sensor_threshold(SensorType.SOIL_MOISTURE, 18.4)
    assert finding is not None
    assert finding["severity"] == "critical"



def test_optimize_crop_rotation_returns_sequence() -> None:
    plan = optimize_crop_rotation(CropType.CORN, SoilType.LOAM, horizon_years=3)
    assert len(plan["sequence"]) == 3
    assert plan["score"] > 0
