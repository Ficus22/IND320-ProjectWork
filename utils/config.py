# utils/config.py

# --- Price Area Mapping ---
PRICE_AREAS = {
    "NO1": {"city": "Oslo", "lat": 59.9139, "lon": 10.7522},
    "NO2": {"city": "Kristiansand", "lat": 58.1467, "lon": 7.9956},
    "NO3": {"city": "Trondheim", "lat": 63.4305, "lon": 10.3951},
    "NO4": {"city": "Tromsø", "lat": 69.6492, "lon": 18.9553},
    "NO5": {"city": "Bergen", "lat": 60.3913, "lon": 5.3221},
}

# --- Open-Meteo API Configuration ---
OPENMETEO_ERA5 = "https://archive-api.open-meteo.com/v1/era5"

DEFAULT_HOURLY_VARIABLES = (
    "temperature_2m",
    "precipitation",
    "wind_speed_10m",
    "wind_gusts_10m",
    "wind_direction_10m"
)

# --- MongoDB Configuration ---
MONGO_COLLECTIONS = ["production_data", "consumption_data"]

# --- Default Settings ---
DEFAULT_YEAR = 2021
MIN_YEAR = 2018
MAX_YEAR = 2024
DEFAULT_PRICE_AREA = "NO1"

# --- Calandar values ---
MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December"
}