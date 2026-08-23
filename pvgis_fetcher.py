import requests
import pandas as pd
import numpy as np
from datetime import datetime
from config import PVGIS_API_URL, LAT, LON, PEAK_KW, SYSTEM_LOSS, AVAILABILITY, DEGRADATION, START_DATE, END_DATE
from utils import save_csv

def fetch_pvgis_hourly(start_date=START_DATE, end_date=END_DATE):
    """
    Fetch hourly PVGIS generation for the Cirata plant.
    Returns DataFrame with timestamp and pvgis_generation_kwh.
    """
    # Use 1 kW reference and scale to plant capacity
    params = {
        "lat": LAT,
        "lon": LON,
        "outputformat": "json",
        "raddatabase": "PVGIS-SARAH2",
        "browser": 0,
        "userhorizon": 1,
        "pvtechchoice": "crystSi",
        "mountingplace": "free",
        "angle": 0,
        "aspect": 0,
        "trackingtype": 2,          # 2-axis tracking
        "pvcalculation": 1,
        "peakpower": 1,             # 1 kW reference
        "loss": SYSTEM_LOSS * 100,  # PVGIS expects percentage
        "startyear": int(start_date[:4]),
        "endyear": int(end_date[:4]),
    }
    try:
        r = requests.get(PVGIS_API_URL, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()
        hourly = data["outputs"]["hourly"]
        df = pd.DataFrame(hourly)
        df["timestamp"] = pd.to_datetime(df["time"], format="%Y%m%d:%H%M")
        # PVGIS P is W per kW installed? Actually P is W for the given peakpower.
        # For reference 1 kW, energy_kwh = P / 1000.
        # Scale to plant peak power (192,000 kW)
        df["pvgis_generation_kwh"] = df["P"] * PEAK_KW / 1000.0
        df = df[["timestamp", "pvgis_generation_kwh"]]
        df = df[(df["timestamp"] >= start_date) & (df["timestamp"] <= end_date)]
        return df
    except Exception as e:
        print(f"[PVGIS] Error: {e}")
        return None

def fetch_and_save_pvgis():
    df = fetch_pvgis_hourly()
    if df is not None:
        save_csv(df, "pvgis_raw.csv")
        print(f"[PVGIS] Saved {len(df)} rows")
    return df
