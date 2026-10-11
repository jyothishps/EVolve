import pandas as pd
from functools import lru_cache
from .config import HISTORY_CSV_PATH, HISTORY_WINDOW


class HistoryUnavailable(Exception):
    pass


@lru_cache(maxsize=1)
def _load_station_histories():
    """
    Read the cleaned CSV once. Rebuild the station code from the one-hot
    columns (ST001 = baseline, all dummies 0) and keep each station's
    loads in time order. Each station has its OWN history - never mixed.
    """
    if not HISTORY_CSV_PATH.exists():
        raise HistoryUnavailable('Historical load data not found. Please contact the administrator.')

    df = pd.read_csv(HISTORY_CSV_PATH, parse_dates=['timestamp'])
    df['station_code'] = 'ST001'
    for col in [c for c in df.columns if c.startswith('station_id_')]:
        df.loc[df[col] == 1, 'station_code'] = col.replace('station_id_', '')

    df = df.sort_values('timestamp')
    return {code: grp['station_load'].tolist() for code, grp in df.groupby('station_code')}


def get_recent_loads(station_code, n=HISTORY_WINDOW):
    """Last n station_load values (oldest -> newest) for ONE station."""
    loads = _load_station_histories().get(station_code, [])
    if len(loads) < n:
        raise HistoryUnavailable(f'Not enough load history for {station_code}.')
    return loads[-n:]