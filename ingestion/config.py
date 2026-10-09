"""Settings for the ingestion pipeline."""
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_ROOT / "data" / "polen.duckdb"
LOG_PATH = PROJECT_ROOT / "logs" / "ingest.log"

# First day of the project period (pollen data starts late 2020)
START_DATE = date(2021, 1, 1)

# Cities from south to north (latitude, longitude)
CITIES = {
    "Malmö":     (55.605, 13.003),
    "Göteborg":  (57.709, 11.974),
    "Stockholm": (59.329, 18.069),
    "Uppsala":   (59.858, 17.639),
    "Umeå":      (63.826, 20.263),
    "Luleå":     (65.584, 22.155),
}

# Cities the pipeline downloads
ACTIVE_CITIES = list(CITIES)

# One raw table per source: raw.<name>
SOURCES = {
    "air_quality": {
        "url": "https://air-quality-api.open-meteo.com/v1/air-quality",
        "variables": [
            "alder_pollen", "birch_pollen", "grass_pollen", "mugwort_pollen",
            "pm2_5", "pm10", "ozone", "nitrogen_dioxide",
        ],
    },
    "weather": {
        "url": "https://archive-api.open-meteo.com/v1/archive",
        "variables": [
            "temperature_2m", "relative_humidity_2m", "precipitation",
            "wind_speed_10m", "wind_direction_10m",
        ],
    },
}
