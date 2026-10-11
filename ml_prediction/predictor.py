import pandas as pd
from .config import (
    SUPPORTED_STATIONS, LOCATION_TYPE_MAP, DEFAULT_LOCATION_CODE,
    DEFAULT_WEATHER, TRAFFIC_LABELS, classify_load,
)
from .model_loader import get_model_bundle, ModelNotAvailable
from .data_loader import get_recent_loads, HistoryUnavailable
from .feature_builder import build_features, estimate_traffic, FeatureError


def _unavailable(message):
    return {'available': False, 'message': message}


def _location_code(station):
    return LOCATION_TYPE_MAP.get((station.location_type or '').strip().lower(), DEFAULT_LOCATION_CODE)


def predict_slots(slots):
    """
    Predict station load (kW) for many slots in ONE model call.
    Returns {slot.id: result}. Never raises - unsupported stations or
    a missing model come back as available=False with a message.
    """
    results = {}
    slots = list(slots)

    try:
        model, feature_columns = get_model_bundle()
    except ModelNotAvailable as e:
        return {s.id: _unavailable(str(e)) for s in slots}

    rows, ids = [], []
    for slot in slots:
        code = slot.station.station_code
        if code not in SUPPORTED_STATIONS:
            results[slot.id] = _unavailable('ML Prediction Unavailable for this Station (model requires retraining).')
            continue
        try:
            loads = get_recent_loads(code)
            rows.append(build_features(
                code, slot.date, slot.start_time, slot.charger.charging_power_kW,
                _location_code(slot.station), loads, feature_columns,
            ))
            ids.append(slot.id)
        except (HistoryUnavailable, FeatureError) as e:
            results[slot.id] = _unavailable(str(e))

    if rows:
        try:
            predictions = model.predict(pd.concat(rows, ignore_index=True))
        except Exception:
            for sid in ids:
                results[sid] = _unavailable('Prediction failed. Please contact the administrator.')
            return results

        slot_by_id = {s.id: s for s in slots}
        for sid, load in zip(ids, predictions):
            load = round(float(load), 1)
            results[sid] = {
                'available': True,
                'load_kw': load,
                'level': classify_load(load),
                'traffic': TRAFFIC_LABELS[estimate_traffic(slot_by_id[sid].start_time.hour)],
                'weather': DEFAULT_WEATHER,
            }
    return results


def predict_slot(slot):
    return predict_slots([slot])[slot.id]