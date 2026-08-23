import json
import sqlite3
import base64
from datetime import datetime, timezone
from web3 import Web3
from config import RPC_URL, PRIVATE_KEY, ACCOUNT_ADDRESS, CONTRACT_ADDRESS, MINT_PER_MWH, DATA_DIR
from utils import load_csv, save_csv
import pandas as pd

def load_contract_abi():
    with open("contract_abi.json") as f:
        data = json.load(f)
    return data["abi"]

def get_contract(w3):
    abi = load_contract_abi()
    return w3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)

def get_ledger():
    path = DATA_DIR / "nft_ledger.csv"
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame(columns=["token_id", "tx_hash", "energy_mwh", "co2_kg", "metadata_uri", "timestamp"])

def mint_eligible_nfts(validated_df):
    if PRIVATE_KEY is None or CONTRACT_ADDRESS is None:
        print("[NFT] PRIVATE_KEY or CONTRACT_ADDRESS not set, skipping mint")
        return

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    assert w3.is_connected(), "RPC not connected"
    acct = w3.eth.account.from_key(PRIVATE_KEY)
    contract = get_contract(w3)

    ledger = get_ledger()
    already_minted = len(ledger)

    # Latest cumulative verified energy in MWh
    latest_verified = validated_df.loc[validated_df["status"] == "VALID", "cumulative_verified_energy_mwh"].max()
    total_eligible = int(latest_verified // MINT_PER_MWH)

    if total_eligible <= already_minted:
        print(f"[NFT] No new NFTs to mint. Minted {already_minted}/{total_eligible}")
        return

    new_mints = total_eligible - already_minted
    print(f"[NFT] Minting {new_mints} new NFTs")

    for i in range(already_minted, total_eligible):
        token_id = i + 1
        energy_mwh = token_id * MINT_PER_MWH  # each NFT = 1 MWh
        co2_kg = energy_mwh * 0.793  # approximate grid emission factor for Indonesia (kg CO2/kWh) adjusted for MWh -> kg
        timestamp_iso = datetime.now(timezone.utc).isoformat()

        metadata = {
            "name": f"Cirata Green Certificate #{token_id}",
            "description": "Proof of Green verified renewable energy certificate",
            "plant": "Cirata Floating Solar",
            "energy_mwh": energy_mwh,
            "co2_kg_offset": co2_kg,
            "validation_source": "NASA POWER vs PVGIS",
            "timestamp": timestamp_iso,
        }
        metadata_b64 = base64.b64encode(json.dumps(metadata).encode()).decode()
        metadata_uri = f"data:application/json;base64,{metadata_b64}"

        tx = contract.functions.safeMint(
            acct.address,
            token_id,
            metadata_uri,
            energy_mwh
        ).build_transaction({
            "from": acct.address,
            "nonce": w3.eth.get_transaction_count(acct.address),
            "gas": 300_000,
            "gasPrice": w3.eth.gas_price,
        })
        signed = acct.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed.rawTransaction)
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        new_row = {
            "token_id": token_id,
            "tx_hash": receipt.transactionHash.hex(),
            "energy_mwh": energy_mwh,
            "co2_kg": co2_kg,
            "metadata_uri": metadata_uri,
            "timestamp": timestamp_iso,
        }
        ledger = pd.concat([ledger, pd.DataFrame([new_row])], ignore_index=True)
        save_csv(ledger, "nft_ledger.csv")
        print(f"[NFT] Minted token {token_id} in tx {receipt.transactionHash.hex()}")

    print(f"[NFT] Done. Total minted: {len(ledger)}")
