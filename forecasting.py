# forecasting.py
import pandas as pd
import numpy as np
import re
import xgboost as xgb

def multi_step_forecast(model: xgb.Booster, features_df: pd.DataFrame, H=4):
    X_new = features_df.reset_index(drop=False)
    if 'date' in X_new.columns:
        X_new = X_new.drop(columns=['date'])
    if 'dengue_total' in X_new.columns:
        X_new = X_new.drop(columns=['dengue_total'])

    Tr_X_cols = X_new.columns.tolist()
    X_new = X_new[Tr_X_cols]

    X_step = X_new.iloc[[-1]].copy()
    lag_cols = [c for c in Tr_X_cols if c.startswith('dengue_total_lag')]
    lag_cols = sorted(lag_cols, key=lambda s: int(re.search(r'lag(\d+)', s).group(1)))
    roll_ws = sorted({int(c.split('_')[-1]) for c in Tr_X_cols if c.startswith('roll_max_')})

    def recompute_rolls_from_recent(Xrow, recent_vals, roll_windows):
        for w in roll_windows:
            vals = np.array(recent_vals[:w], dtype=float)
            Xrow[f'roll_max_{w}'] = float(np.max(vals))
            Xrow[f'roll_min_{w}'] = float(np.min(vals))
            Xrow[f'roll_std_{w}'] = float(np.std(vals, ddof=0))
        return Xrow

    recent = [ float(X_step.iloc[0][c]) for c in lag_cols ]
    max_w = max(roll_ws) if roll_ws else len(recent)
    if len(recent) < max_w:
        recent += [recent[-1]] * (max_w - len(recent))

    base_date = pd.to_datetime(features_df.index[-1])
    forecast_dates = []
    forecast_values = []

    for h in range(1, H+1):
        dmat = xgb.DMatrix(X_step.values, feature_names=Tr_X_cols)
        pred = float(model.predict(dmat)[0])
        forecast_values.append(pred)
        forecast_dates.append(base_date + pd.Timedelta(weeks=h))

        recent.insert(0, pred)
        recent = recent[:max_w]

        for i, col in enumerate(lag_cols):
            X_step.at[X_step.index[0], col] = float(recent[i]) if i < len(recent) else float(recent[-1])

        X_step = recompute_rolls_from_recent(X_step.iloc[0].copy(), recent, roll_ws).to_frame().T
        X_step = X_step[Tr_X_cols]

        if 'weekofyear' in X_step.columns:
            w = int(X_step.iloc[0]['weekofyear'])
            X_step.at[X_step.index[0], 'weekofyear'] = (w % 52) + 1

    forecast_df = pd.DataFrame({'forecast': np.array(forecast_values)}, index=pd.to_datetime(forecast_dates))
    return forecast_df
