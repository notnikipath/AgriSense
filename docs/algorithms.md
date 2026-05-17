# Algorithms

## Sensor thresholding

Threshold checks classify readings into normal, warning, or critical windows by sensor type. Soil moisture under lower bound raises critical drought alerts.

## Irrigation recommendation

Irrigation demand is computed from moisture deficit, crop target moisture, and temperature heat factor. Auto mode converts recommendation into actionable control events.

## Fertilizer optimization

Dosage combines target yield, crop factor, soil factor, and NDVI vegetation factor. Formula recommendation includes NPK profile and magnesium extension for sandy or clay soils.

## Yield forecast

Forecast uses a deterministic ML-like scoring model over moisture, temperature, light, rainfall, and NDVI, with ongoing MAPE tracking.

## Crop rotation optimization

Rotation planner generates a multi-year sequence and score based on current crop, soil type, and diversity.

## Realtime telemetry scaling

Worker and partition plan is computed from sensor count and region count to support high-volume ingestion.

## Map caching and offline packages

Map tile count is estimated from field area and zoom level, then reused through TTL cache. Offline map package size is estimated for mobile delivery.
