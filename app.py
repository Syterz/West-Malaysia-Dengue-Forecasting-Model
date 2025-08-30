from flask import Flask, jsonify, Response
import xgboost as xgb
from data_utils import fetch_weather_power, load_dengue_cases_from_gsheet, daily_to_weekly, construct_features_for_model, fill_missing_week_dates
from forecasting import multi_step_forecast
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import io
import matplotlib.dates as mdates


app = Flask(__name__)

GSHEET_URL = "https://docs.google.com/spreadsheets/d/1KlsXDWymnydc4lIloxBuQLuLuLvhgDugIevo2_s5xoU/export?format=xlsx"

today = datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).date()
days_since_sunday = (today.weekday() - 6) % 7
last_sunday = today - timedelta(days=days_since_sunday)

# --- CONFIG ---
MODEL_PATH = "models/xgb_dengue.json"
DENGUE_EXCEL_PATH = "data/Weekly new cases.xlsx"
LAT, LON = 3.0728, 101.4235
# NASA POWER uses YYYYMMDD strings
WEATHER_START = "20250519"
WEATHER_END = last_sunday.strftime("%Y%m%d")
FORECAST_HORIZON = 4
MODEL_PATH = "models/xgb_dengue.json"
DENGUE_EXCEL_PATH = "data/Weekly new cases.xlsx"


# Load model
booster = xgb.Booster()
booster.load_model(MODEL_PATH)

@app.route("/healthz")
def healthz():
    return jsonify({"status":"ok", "weather_end": WEATHER_END, "weather_start": WEATHER_START})

@app.route("/forecast", methods=["GET"])
def forecast_endpoint():
    try:
        daily_weather = fetch_weather_power(LAT, LON, WEATHER_START, WEATHER_END)
        dengue_daily = load_dengue_cases_from_gsheet(GSHEET_URL)
        dd = dengue_daily.reset_index()
        dd_filled = fill_missing_week_dates(dd, date_col='date')
        dengue_daily = dd_filled.set_index('date').sort_index()
        combined = daily_to_weekly(daily_weather, dengue_daily)
        features = construct_features_for_model(combined)
        forecast_df = multi_step_forecast(booster, features, H=FORECAST_HORIZON)
        out = {
            "forecast_horizon_weeks": FORECAST_HORIZON,
            "last_data_week": str(features.index[-1]),
            "forecasts": [
                {"date": str(idx.date()), "predicted_cases": float(v)}
                for idx, v in forecast_df['forecast'].items()
            ]
        }
        return jsonify(out)
    except Exception as e:
        app.logger.exception("Error in /forecast")
        return jsonify({"error": str(e)}), 500

@app.route("/plot", methods=["GET"])
def plot_forecast():
    try:
        daily_weather = fetch_weather_power(LAT, LON, WEATHER_START, WEATHER_END)
        dengue_daily = load_dengue_cases_from_gsheet(GSHEET_URL)
        dd = dengue_daily.reset_index() 
        dd_filled = fill_missing_week_dates(dd, date_col='date')
        dengue_daily = dd_filled.set_index('date').sort_index()
        print(dengue_daily)
        combined = daily_to_weekly(daily_weather, dengue_daily)
        features = construct_features_for_model(combined)
        forecast_df = multi_step_forecast(booster, features, H=FORECAST_HORIZON)

        # Start plotting
        fig, ax = plt.subplots(figsize=(10, 5))

        # Plot observed
        ax.plot(dengue_daily.index, dengue_daily['dengue_total'], 
                label="Observed", color="blue")

        # Connect last observed → first forecast
        last_obs_date = dengue_daily.index[-1]
        last_obs_value = dengue_daily['dengue_total'].iloc[-1]

        forecast_with_start = pd.concat([
            pd.DataFrame({"forecast": [last_obs_value]}, index=[last_obs_date]),
            forecast_df
        ])

        ax.plot(forecast_with_start.index, forecast_with_start['forecast'], 
                label="Forecast", color="red")
    
        ax.xaxis.set_major_locator(mdates.WeekdayLocator(byweekday=6))
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        fig.autofmt_xdate()

        ax.axvline(x=last_obs_date, color="gray", linestyle="--")  # forecast start marker
        ax.legend()

        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        buf.seek(0)
        plt.close(fig)  # free memory

        return Response(buf.getvalue(), mimetype="image/png")
    except Exception as e:
        app.logger.exception("Error in /plot")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)