from shared.agrisense_common import (
    fertilizer_need_kg_ha,
    irrigation_need_liters_per_ha,
    offline_pack_size_mb,
    telemetry_realtime_plan,
    yield_mape,
)
from shared.agrisense_common.schemas import CropType, SoilType


def test_yield_mape() -> None:
    assert yield_mape([5.9, 6.0], [6.1, 5.8]) > 0



def test_irrigation_and_fertilizer_ranges() -> None:
    irrigation = irrigation_need_liters_per_ha(28, 31, CropType.CORN)
    fertilizer = fertilizer_need_kg_ha(CropType.CORN, SoilType.LOAM, 8.2, 0.52)
    assert irrigation >= 0
    assert fertilizer > 0



def test_realtime_plan_has_workers() -> None:
    plan = telemetry_realtime_plan(10000, 8)
    assert plan["workers"] >= 2
    assert plan["batch_size"] >= 100



def test_offline_pack_size_positive() -> None:
    assert offline_pack_size_mb(120, 16) > 0
