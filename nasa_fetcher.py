import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config import NASA_API_URL, LAT, LON, NASA_PARAMETERS, START_DATE, END_DATE, PEAK_KW, SYSTEM_LOSS, AVAILABILITY, DEGRADATION
from utils import save_csv

def fetch_nasa_hourly(start_date=START_DATE, end_date=END_DATE):
    """
    Fetch hourly NASA POWER data.
    Returns DataFrame with timestamp, irradiance, weather, expected generation.
    """
    # NASA POWER endpoint accepts start/end in YYYYMMDD
    start = pd.Timestamp(start_date).strftime("%Y%m%d")
    end = pd.Timestamp(end_date).strftime("%Y%m%d")

    all_frames = []
    # NASA API may limit range; fetch in yearly chunks
    current = pd.Timestamp(start_date)
    end_ts = pd.Timestamp(end_date)
    while current < end_ts:
        chunk_end = min(current + pd.DateOffset(years=1) - pd.Timedelta(days=1), end_ts)
        params = {
            "parameters": NASA_PARAMETERS,
            "community": "RE",
            "longitude": LON,
            "latitude": LAT,
            "start": current.strftime("%Y%m%d"),
            "end": chunk_end.strftime("%Y%m%d"),
            "format": "JSON",
        }
        try:
            r = requests.get(NASA_API_URL, params=params, timeout=60)
            r.raise_for_status()
            data = r.json()
            props = data["properties"]["parameter"]
            df = pd.DataFrame(props)
            df.index = pd.to_datetime(df.index)
            df = df.reset_index().rename(columns={"index": "timestamp"})
            all_frames.append(df)
        except Exception as e:
            print(f"[NASA] Error for {current}-{chunk_end}: {e}")
        current = chunk_end + pd.Timedelta(days=1)

    if not all_frames:
        return None

    nasa = pd.concat(all_frames, ignore_index=True).sort_values("timestamp")
    nasa = nasa.rename(columns={
        "ALLSKY_SFC_SW_DWN": "irradiance_wh_m2",
        "T2M": "temperature_c",
        "RH2M": "humidity_percent",
        "WS10M": "wind_speed_ms",
        "CLRSKY_SFC_SW_DWN": "clear_sky_irradiance_wh_m2",
    })

    # Compute cloud cover estimate
    nasa["cloud_cover_percent"] = (
        1 - nasa["irradiance_wh_m2"] / nasa["clear_sky_irradiance_wh_m2"].replace(0, np.nan)
    ).clip(0, 1) * 100

    # Expected generation: simple model
    # energy_kwh = irradiance_wh_m2 / 1000 * capacity_kW * PR * availability * degradation
    days_since_start = (nasa["timestamp"] - pd.Timestamp(START_DATE)).dt.days / 365.25
    degradation_factor = (1 - DEGRADATION) ** days_since_start
    performance_ratio = (1 - SYSTEM_LOSS)
    nasa["nasa_expected_kwh"] = (
        nasa["irradiance_wh_m2"] / 1000
        * PEAK_KW
        * performance_ratio
        * AVAILABILITY
        * degradation_factor
    )

    cols = [
        "timestamp", "irradiance_wh_m2", "clear_sky_irradiance_wh_m2",
        "cloud_cover_percent", "temperature_c", "humidity_percent",
        "wind_speed_ms", "nasa_expected_kwh"
    ]
    return nasa[cols]

def fetch_and_save_nasa():
    df = fetch_nasa_hourly()
    if df is not None:
        save_csv(df, "nasa_raw.csv")
        print(f"[NASA] Saved {len(df)} rows")
    return df
