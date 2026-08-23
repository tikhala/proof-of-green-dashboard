import pandas as pd
from pathlib import Path
from config import DATA_DIR

def save_csv(df, filename):
    path = DATA_DIR / filename
    df.to_csv(path, index=False)
    return path

def load_csv(filename):
    path = DATA_DIR / filename
    if path.exists():
        return pd.read_csv(path, parse_dates=["timestamp"])
    return pd.DataFrame()

def ensure_data_dir():
    DATA_DIR.mkdir(exist_ok=True)
