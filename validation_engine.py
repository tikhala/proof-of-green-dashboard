import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from config import VALIDATION_THRESHOLD
from utils import save_csv

def validate_generation(pvgis_df, nasa_df):
    """
    Merge PVGIS and NASA data, validate, and compute cumulative verified energy.
    """
    if pvgis_df is None or nasa_df is None:
        raise ValueError("Missing PVGIS or NASA data")

    merged = pd.merge(pvgis_df, nasa_df, on="timestamp", how="inner")
    merged = merged.sort_values("timestamp").reset_index(drop=True)

    # Normalized difference
    merged["diff_ratio"] = (
        (merged["pvgis_generation_kwh"] - merged["nasa_expected_kwh"])
        / merged["nasa_expected_kwh"].replace(0, np.nan)
    )
    merged["validation_score"] = 1 - merged["diff_ratio"].abs().clip(0, 1)
    merged["status"] = np.where(
        merged["diff_ratio"].abs() > VALIDATION_THRESHOLD,
        "INVALID",
        "VALID"
    )

    # Optional anomaly detection (IsolationForest) to catch outliers
    # Use only when there are enough points
    if len(merged) > 100:
        features = merged[["pvgis_generation_kwh", "nasa_expected_kwh"]].fillna(0)
        iso = IsolationForest(contamination=0.02, random_state=42)
        merged["anomaly"] = iso.fit_predict(features)
        merged.loc[merged["anomaly"] == -1, "status"] = "INVALID"
        merged.drop(columns=["anomaly"], inplace=True)

    # Cumulative verified energy (only VALID rows)
    merged["cumulative_verified_energy_mwh"] = np.where(
        merged["status"] == "VALID",
        merged["pvgis_generation_kwh"] / 1000,  # kWh -> MWh
        0
    ).cumsum()

    final_cols = [
        "timestamp",
        "pvgis_generation_kwh",
        "nasa_expected_kwh",
        "diff_ratio",
        "validation_score",
        "status",
        "cumulative_verified_energy_mwh",
        "cloud_cover_percent",
        "humidity_percent",
        "temperature_c",
    ]
    result = merged[final_cols]
    return result

def run_validation():
    from pvgis_fetcher import fetch_and_save_pvgis
    from nasa_fetcher import fetch_and_save_nasa

    pvgis = fetch_and_save_pvgis()
    nasa = fetch_and_save_nasa()
    validated = validate_generation(pvgis, nasa)
    save_csv(validated, "validated_data.csv")
    print(f"[Validation] Valid rows: {(validated['status'] == 'VALID').sum()}, Invalid: {(validated['status'] == 'INVALID').sum()}")
    return validated
