import pandas as pd
from .config import (
    PEAK_HOURS, MEDIUM_TRAFFIC_HOURS, SUPPORTED_STATIONS,
    DEFAULT_BATTERY_KWH, DEFAULT_INITIAL_SOC, DEFAULT_ELECTRICITY_PRICE,
    DEFAULT_WEATHER,
)


class FeatureError(Exception):
    pass


def estimate_traffic(hour):
    """Estimated traffic (0 Low, 1 Medium, 2 High) - same pattern as the dataset."""
    if hour in PEAK_HOURS:
        return 2
    if hour in MEDIUM_TRAFFIC_HOURS:
        return 1
    return 0


def build_features(station_code, slot_date, start_time, charger_kw,
                   location_code, loads, feature_columns,
                   weather=DEFAULT_WEATHER, vehicle_type='Car',
                   battery_kwh=DEFAULT_BATTERY_KWH, initial_soc=DEFAULT_INITIAL_SOC):
    """
    Build ONE row with exactly the trained columns, in the saved order.
    `loads` = last 10 loads of THIS station (oldest -> newest).
    """
    if station_code not in SUPPORTED_STATIONS:
        raise FeatureError('ML Prediction Unavailable for this Station (model requires retraining).')
    if len(loads) < 10:
        raise FeatureError('Not enough load history to predict.')

    hour = start_time.hour
    is_peak = 1 if hour in PEAK_HOURS else 0

    values = {
        'location_type': location_code,
        'battery_capacity_kWh': battery_kwh,
        'initial_soc': initial_soc,
        'charging_power_kW': charger_kw,
        'electricity_price': DEFAULT_ELECTRICITY_PRICE,
        'traffic_density': estimate_traffic(hour),
        'time_slot': is_peak,                       # identical to is_peak_hour in the dataset
        'hour': hour,
        'day': slot_date.day,
        'month': slot_date.month,
        'day_of_week_num': slot_date.weekday(),
        'is_weekend': 1 if slot_date.weekday() >= 5 else 0,
        'week_of_year': slot_date.isocalendar()[1],
        'is_peak_hour': is_peak,
        'load_lag_1': loads[-1],
        'load_lag_2': loads[-2],
        'load_lag_3': loads[-3],
        'load_rolling_mean_5': sum(loads[-5:]) / 5,
        'load_rolling_mean_10': sum(loads[-10:]) / 10,
        # Bus = baseline: both vehicle dummies stay 0
        'vehicle_type_Car': 1 if vehicle_type == 'Car' else 0,
        'vehicle_type_Two-Wheeler': 1 if vehicle_type == 'Two-Wheeler' else 0,
        'weather_condition_Cloudy': 1 if weather == 'Cloudy' else 0,
        'weather_condition_Rainy': 1 if weather == 'Rainy' else 0,
    }
    if station_code != 'ST001':                      # ST001 = dropped baseline
        values['station_id_' + station_code] = 1

    unknown = set(values) - set(feature_columns)
    if unknown:
        raise FeatureError(f'Feature mismatch with trained model: {sorted(unknown)}')

    row = {col: 0 for col in feature_columns}
    row.update(values)
    return pd.DataFrame([row])[feature_columns]