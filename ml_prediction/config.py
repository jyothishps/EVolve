from pathlib import Path
from django.conf import settings

BASE_DIR = Path(settings.BASE_DIR)

MODEL_PATH = BASE_DIR / 'ml_models' / 'random_forest_ev_load_2026_tuned.pkl'
FEATURES_PATH = BASE_DIR / 'ml_models' / 'ev_load_feature_columns.pkl'
HISTORY_CSV_PATH = BASE_DIR / 'ml_prediction' / 'data' / 'ev_load_historical_cleaned.csv'

# Stations the trained model knows. Anything else = "Prediction Unavailable".
SUPPORTED_STATIONS = [f'ST{i:03d}' for i in range(1, 21)]

# Load classification thresholds (kW). One place only - templates never hardcode these.
LOW_MAX = 40
PEAK_MIN = 70


def classify_load(load_kw):
    if load_kw < LOW_MAX:
        return 'Low'
    if load_kw < PEAK_MIN:
        return 'Normal'
    return 'Peak'


# Same hour ranges used when the dataset was preprocessed
PEAK_HOURS = set(range(7, 11)) | set(range(17, 22))
MEDIUM_TRAFFIC_HOURS = set(range(11, 17))
TRAFFIC_LABELS = {0: 'Low', 1: 'Medium', 2: 'High'}

# Same encoding used in training: {Highway: 0, Urban: 1}
LOCATION_TYPE_MAP = {'highway': 0, 'urban': 1}
DEFAULT_LOCATION_CODE = 1

# Unknown-vehicle defaults (dataset means). Shown as "estimated" in the UI.
DEFAULT_BATTERY_KWH = 60
DEFAULT_INITIAL_SOC = 34.8
DEFAULT_ELECTRICITY_PRICE = 9.96
DEFAULT_WEATHER = 'Clear'          # Clear / Cloudy / Rainy

# lag_1..3 and rolling_5/10 need the last 10 loads of the station
HISTORY_WINDOW = 10