import datetime
import pandas as pd
from django.core.management.base import BaseCommand
from ml_prediction.config import HISTORY_CSV_PATH, classify_load
from ml_prediction.model_loader import get_model_bundle
from ml_prediction.data_loader import get_recent_loads
from ml_prediction.feature_builder import build_features


class Command(BaseCommand):
    help = 'Checks the ML model, feature order and prediction pipeline.'

    def handle(self, *args, **options):
        model, cols = get_model_bundle()
        self.stdout.write(f'Model loaded. Features: {len(cols)}')

        # Test 1: saved feature list matches the CSV and the model
        df = pd.read_csv(HISTORY_CSV_PATH)
        pred = model.predict(df[cols])
        mae = (pd.Series(pred) - df['station_load']).abs().mean()
        self.stdout.write(f'Test 1 - CSV rows: {len(df)}, MAE on cleaned data: {mae:.2f} kW (train+test mix, expect ~5-8)')

        # Test 2: Django feature builder for ST001, every hour of one day
        loads = get_recent_loads('ST001')
        day = datetime.date.today()
        self.stdout.write('Test 2 - ST001 predicted load by hour (expect ~24 / ~50 / ~84 tiers):')
        for hour in range(24):
            X = build_features('ST001', day, datetime.time(hour, 0), 22, 1, loads, cols)
            load = float(model.predict(X)[0])
            self.stdout.write(f'  {hour:02d}:00  {load:6.1f} kW  {classify_load(load)}')