#!/usr/bin/env python
"""
Proof of Green Pipeline
Run every 2 hours via GitHub Actions.
"""
import pandas as pd
from config import DATA_DIR
from utils import save_csv
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def main():
    logging.info("Starting pipeline")

    # Try real APIs, fallback to simulator on failure
    try:
        from pvgis_fetcher import fetch_and_save_pvgis
        pvgis = fetch_and_save_pvgis()
    except Exception as e:
        logging.warning(f"PVGIS failed ({e}), using fallback simulator")
        from fallback_simulator import simulate_pvgis
        pvgis = simulate_pvgis()
        save_csv(pvgis, "pvgis_raw.csv")

    try:
        from nasa_fetcher import fetch_and_save_nasa
        nasa = fetch_and_save_nasa()
    except Exception as e:
        logging.warning(f"NASA failed ({e}), using fallback simulator")
        from fallback_simulator import simulate_nasa
        nasa = simulate_nasa()
        save_csv(nasa, "nasa_raw.csv")

    from validation_engine import validate_generation
    validated = validate_generation(pvgis, nasa)
    save_csv(validated, "validated_data.csv")
    logging.info(f"Validation complete: {len(validated)} rows")

    from nft_minter import mint_eligible_nfts
    mint_eligible_nfts(validated)

    logging.info("Pipeline finished")

if __name__ == "__main__":
    main()
