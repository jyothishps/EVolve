import joblib
from functools import lru_cache
from .config import MODEL_PATH, FEATURES_PATH


class ModelNotAvailable(Exception):
    pass


@lru_cache(maxsize=1)
def get_model_bundle():
    """
    Load model + exact feature order ONCE and reuse (cached in memory).
    If files are missing we raise a clean error instead of crashing the site.
    A failed load is not cached, so it retries after the files are fixed.
    """
    if not MODEL_PATH.exists() or not FEATURES_PATH.exists():
        raise ModelNotAvailable('ML model file not found. Please contact the administrator.')
    try:
        model = joblib.load(MODEL_PATH)
        feature_columns = joblib.load(FEATURES_PATH)
    except Exception:
        raise ModelNotAvailable('ML model could not be loaded. Please contact the administrator.')

    if len(feature_columns) != model.n_features_in_:
        raise ModelNotAvailable('ML model and feature list do not match. Please contact the administrator.')
    return model, list(feature_columns)