# data_utils.py
import requests
import pandas as pd

def fetch_weather_power(lat, lon, start_date, end_date, params="T2M,RH2M,PRECTOTCORR,WS2M"):
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    req = {
        "parameters": params,
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": start_date,
        "end": end_date,
        "format": "JSON"
    }
    r = requests.get(url, params=req, timeout=30)
    r.raise_for_status()
    data = r.json()
    results = data["properties"]["parameter"]
    df = pd.DataFrame({
        "date": list(results["T2M"].keys()),
        "T2M": list(results["T2M"].values()),
        "RH2M": list(results["RH2M"].values()),
        "WS2M": list(results["WS2M"].values()),
        "PRECTOTCORR": list(results["PRECTOTCORR"].values())
    })
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    return df

def load_dengue_cases_from_gsheet(excel_url: str):
    df = pd.read_excel(excel_url, parse_dates=['date'])
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.set_index('date')
    df.columns = [c.strip().lower() for c in df.columns]
    if 'total' in df.columns:
        df = df[['total']].rename(columns={'total': 'dengue_total'})
    elif 'dengue_total' in df.columns:
        df = df[['dengue_total']]
    else:
        raise ValueError(f"Excel must contain 'Total' or 'dengue_total'. Found columns: {df.columns.tolist()}")
    return df

def fill_missing_week_dates(df, date_col='date'):

    # Ensures all rows have a date, because for some God forsaken reason there are those that doesn't?

    df = df.copy()
    df = df.reset_index(drop=True)

    n = len(df)
    if n == 0:
        return df

    # Convert to numpy array style for faster in-place updates
    dates = df[date_col].values

    for i in range(1, n):
        if pd.isna(dates[i]):
            prev = pd.to_datetime(dates[i-1])
            dates[i] = prev + pd.Timedelta(days=7)

    df[date_col] = pd.to_datetime(dates)
    return df


def daily_to_weekly(weather_df, dengue_df):
    agg_dict = {
        'T2M':         'mean',
        'RH2M':        'mean',
        'PRECTOTCORR': 'sum',
        'WS2M':        'mean',
    }
    weekly_w = weather_df.resample('W-MON').agg(agg_dict)
    weekly_w.index = weekly_w.index - pd.Timedelta(days=1)
    dengue_weekly = dengue_df.resample('W-MON').sum()
    dengue_weekly.index = dengue_weekly.index - pd.Timedelta(days=1)
    combined = weekly_w.join(dengue_weekly, how='outer')
    return combined

def make_lag_features(df, target_col, max_lag):
    df = df.copy()
    for lag in range(1, max_lag + 1):
        df[f"{target_col}_lag{lag}"] = df[target_col].shift(lag)
    return df

def construct_features_for_model(combined_df):
    df = combined_df.copy()
    if 'Total' in df.columns and 'dengue_total' not in df.columns:
        df = df.rename(columns={'Total':'dengue_total'})
    df = make_lag_features(df, 'dengue_total', 2)
    df["weekofyear"] = df.index.isocalendar().week.astype(int)
    df['T2M_1w_lag'] = df['T2M'].shift(1)
    df['T2M_5w_lag'] = df['T2M'].shift(5)
    df['ws2m_3w_lag'] = df['WS2M'].shift(3)
    df['precip_4w_lag'] = df['PRECTOTCORR'].shift(4)
    df['precip_6w_lag'] = df['PRECTOTCORR'].shift(6)
    df['precip_mean_8_shift_2'] = df['PRECTOTCORR'].shift(8).rolling(window=2).mean()
    windows = [2,3]
    for w in windows:
        df[f'roll_max_{w}'] = df['dengue_total'].rolling(window=w).max()
        df[f'roll_min_{w}'] = df['dengue_total'].rolling(window=w).min()
        df[f'roll_std_{w}'] = df['dengue_total'].rolling(window=w).std()
    df.drop(['WS2M','RH2M','PRECTOTCORR','T2M','roll_std_3'], axis=1, errors='ignore', inplace=True)
    df.dropna(inplace=True)
    return df