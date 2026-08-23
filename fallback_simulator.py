import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from config import START_DATE, END_DATE, PEAK_KW, SYSTEM_LOSS, AVAILABILITY, DEGRADATION, LAT, LON

def simulate_pvgis(start_date=START_DATE, end_date=END_DATE):
    """Generate synthetic PVGIS-like hourly data."""
    hours = pd.date_range(start=start_date, end=end_date, freq="H", tz="Asia/Jakarta")
    # Simple daylight curve
    hour_of_day = hours.hour
    daylight = np.sin(np.pi * (hour_of_day - 6) / 12)
    daylight = np.clip(daylight, 0, 1)
    seasonal = 1 + 0.1 * np.sin(2 * np.pi * (hours.dayofyear - 172) / 365)
    output = daylight * seasonal * PEAK_KW * (1 - SYSTEM_LOSS) * AVAILABILITY * 0.8
    df = pd.DataFrame({"timestamp": hours, "pvgis_generation_kwh": output})
    return df

def simulate_nasa(start_date=START_DATE, end_date=END_DATE):
    """Generate synthetic NASA-like hourly data."""
    hours = pd.date_range(start=start_date, end=end_date, freq="H", tz="Asia/Jakarta")
    hour_of_day = hours.hour
    daylight = np.sin(np.pi * (hour_of_day - 6) / 12)
    daylight = np.clip(daylight, 0, 1)
    irradiance = daylight * 900  # W/m2 max
    clear_sky = np.clip(daylight * 1000, 0, 1000)
    cloud = 1 - irradiance / clear_sky.replace(0, np.nan)
    cloud = cloud.fillna(0).clip(0, 1) * 100
    temp = 25 + 5 * np.sin(2 * np.pi * (hours.hour - 14) / 24)
    humidity = 70 + 10 * np.cos(2 * np.pi * (hours.hour - 10) / 24)
    wind = 3 + 2 * np.random.rand(len(hours))
    expected = irradiance / 1000 * PEAK_KW * (1 - SYSTEM_LOSS) * AVAILABILITY * 0.95
    df = pd.DataFrame({
        "timestamp": hours,
        "irradiance_wh_m2": irradiance,
        "clear_sky_irradiance_wh_m2": clear_sky,
        "cloud_cover_percent": cloud,
        "temperature_c": temp,
        "humidity_percent": humidity,
        "wind_speed_ms": wind,
        "nasa_expected_kwh": expected,
    })
    return df
