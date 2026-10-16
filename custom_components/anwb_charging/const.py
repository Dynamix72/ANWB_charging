DOMAIN = "anwb_charging"

CONF_DEVICE_TRACKER = "device_tracker"
CONF_RADIUS = "radius"

CONF_MIN_POWER_KW = "min_power_kw"
CONF_MAX_DETOUR_KM = "max_detour_km"
CONF_ORS_API_KEY = "ors_api_key"
CONF_CHARGER_TYPE = "charger_type"
CONF_DESTINATION = "destination"
CONF_DATA_MODE = "data_mode"
CONF_FUEL_TYPE = "fuel_type"

DEFAULT_RADIUS = 10  # Vast ingesteld op 10 km (niet aanpasbaar)
DEFAULT_MIN_POWER_KW = 0  # 0 = alle typen
DEFAULT_MAX_DETOUR_KM = 10  # Maximum omrijden in km
DEFAULT_CHARGER_TYPE = "Alle laders"
DEFAULT_DESTINATION = ""
DEFAULT_DATA_MODE = "chargers"
DEFAULT_FUEL_TYPE = "euro95"

CHARGER_TYPES = [
    "Alle laders",
    "AC laders",
    "Snelladers",
    "Ultrasnelladers",
]

DATA_MODES = [
    "chargers",
    "fuels",
    "both",
]

FUEL_TYPES = [
    "euro95",
    "diesel",
    "autogas",
]
