import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Plant constants
PLANT_NAME = "Cirata Floating Solar"
LAT = -6.702
LON = 107.367
TZ = "Asia/Jakarta"
CAPACITY_MW = 145          # AC capacity
PEAK_MW = 192              # DC capacity
PEAK_KW = PEAK_MW * 1000   # 192,000 kW
PANELS = 340_000
CLUSTERS = 13
ANNUAL_GEN_GWH = 270       # midpoint 240-300
ANNUAL_CO2_TONNES = 214_000
START_DATE = "2023-11-09"
END_DATE = "2026-08-09"

# PVGIS assumptions
SYSTEM_LOSS = 0.14         # 14%
AVAILABILITY = 0.98
DEGRADATION = 0.005        # 0.5% per year
PVGIS_TRACKING = True
PVGIS_OFFGRID = False      # PVGIS offgrid not directly supported; keep False

# Validation
VALIDATION_THRESHOLD = 0.15   # 15% normalized difference
MINT_PER_MWH = 1              # 1 NFT per 1 MWh verified

# NASA
NASA_PARAMETERS = "ALLSKY_SFC_SW_DWN,T2M,RH2M,WS10M,CLRSKY_SFC_SW_DWN"

# Web3
RPC_URL = os.getenv("RPC_URL", "https://rpc-amoy.polygon.technology")
CHAIN_ID = int(os.getenv("CHAIN_ID", 80002))
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ACCOUNT_ADDRESS = os.getenv("ACCOUNT_ADDRESS")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

# Data repo
PUBLIC_DATA_REPO = os.getenv("PUBLIC_DATA_REPO", "yourusername/proof-of-green-data")
