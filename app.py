import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz

st.set_page_config(page_title="Proof of Green — Cirata Solar", layout="wide")
st.title("🔆 Proof of Green: Cirata Floating Solar Digital Twin")

# Public data repo raw URLs
DATA_REPO = "https://raw.githubusercontent.com/tikhala/proof-of-green-data/main"
VALIDATED_URL = f"{DATA_REPO}/validated_data.csv"
NFT_LEDGER_URL = f"{DATA_REPO}/nft_ledger.csv"

@st.cache_data(ttl=120)  # refresh every 2 minutes
def load_data(url):
    try:
        return pd.read_csv(url, parse_dates=["timestamp"])
    except Exception as e:
        st.error(f"Failed to load {url}: {e}")
        return pd.DataFrame()

validated = load_data(VALIDATED_URL)
nft_ledger = load_data(NFT_LEDGER_URL)

if validated.empty:
    st.warning("No data found. Run the pipeline first.")
    st.stop()

# Current time in Jakarta
jakarta = pytz.timezone("Asia/Jakarta")
now = datetime.now(jakarta)
st.caption(f"Last refresh: {now.strftime('%Y-%m-%d %H:%M:%S WIB')} | Data updates every 2 hours")

# Top KPI cards
col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Minted NFTs", len(nft_ledger) if not nft_ledger.empty else 0)
col2.metric("Carbon Saved (tonnes)", f"{validated['pvgis_generation_kwh'].sum() * 0.793 / 1000:,.0f}")
col3.metric("Plant Capacity", "192 MWp / 145 MWac")
col4.metric("Current Date", now.strftime("%d %b %Y"))
col5.metric("Cloud Cover", f"{validated.iloc[-1]['cloud_cover_percent']:.0f}%")
col6.metric("Humidity", f"{validated.iloc[-1]['humidity_percent']:.0f}%")

st.markdown("---")

# Main visualization
st.subheader("PVGIS Model vs NASA Validation")
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=validated["timestamp"],
    y=validated["pvgis_generation_kwh"],
    mode="lines",
    name="PVGIS (Digital Twin)",
    line=dict(color="blue", width=0.8),
))
fig.add_trace(go.Scatter(
    x=validated["timestamp"],
    y=validated["nasa_expected_kwh"],
    mode="lines",
    name="NASA Expected",
    line=dict(color="orange", width=0.8),
))
# Mark invalid points
invalid = validated[validated["status"] == "INVALID"]
fig.add_trace(go.Scatter(
    x=invalid["timestamp"],
    y=invalid["pvgis_generation_kwh"],
    mode="markers",
    name="Invalid",
    marker=dict(color="red", size=3),
))
fig.update_layout(height=450, margin=dict(l=0, r=0, t=30, b=0),
                  legend=dict(orientation="h", yanchor="bottom", y=1.02))
st.plotly_chart(fig, use_container_width=True)

# Additional data story
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Cumulative Energy", "NFT Activity", "Monthly Summary", "Validation Pass Rate", "ESG-Lite Report"
])

with tab1:
    st.subheader("Cumulative Verified Energy")
    fig = px.area(validated, x="timestamp", y="cumulative_verified_energy_mwh",
                  title="Verified Energy (MWh)")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Recent NFT Mints")
    if not nft_ledger.empty:
        st.dataframe(nft_ledger[["token_id", "tx_hash", "energy_mwh", "co2_kg", "timestamp"]].tail(20))
    else:
        st.info("No NFTs minted yet. Pipeline will mint after validation.")

with tab3:
    st.subheader("Monthly Energy Generation")
    monthly = validated.set_index("timestamp").resample("M").sum(numeric_only=True)
    monthly["month"] = monthly.index.strftime("%b %Y")
    fig = px.bar(monthly, x="month", y="pvgis_generation_kwh", title="Monthly Generation (kWh)")
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Validation Pass Rate")
    total = len(validated)
    valid_count = (validated["status"] == "VALID").sum()
    invalid_count = total - valid_count
    st.write(f"Valid: {valid_count} ({valid_count/total:.1%})")
    st.write(f"Invalid: {invalid_count} ({invalid_count/total:.1%})")
    fig = px.pie(values=[valid_count, invalid_count], names=["Valid", "Invalid"],
                 title="Validation Status Distribution")
    st.plotly_chart(fig, use_container_width=True)

with tab5:
    st.subheader("ESG-Lite / Non-Audited Report")
    st.markdown("**Cirata Floating Solar Plant — Proof of Green**")
    st.write(f"Period: 9 Nov 2023 to 9 Aug 2026")
    st.write(f"Total PVGIS generation: {validated['pvgis_generation_kwh'].sum():,.0f} kWh")
    st.write(f"Total NASA expected generation: {validated['nasa_expected_kwh'].sum():,.0f} kWh")
    st.write(f"Total verified energy: {validated['cumulative_verified_energy_mwh'].max():,.0f} MWh")
    st.write(f"NFTs minted: {len(nft_ledger) if not nft_ledger.empty else 0}")
    st.write(f"Assumed CO₂ offset: {validated['pvgis_generation_kwh'].sum() * 0.793 / 1000:,.0f} tonnes")
    st.write(f"Assumed emission factor: 0.793 kg CO₂/kWh (Indonesia grid average)")
    st.download_button(
        "Download Report (HTML)",
        data=st._get_report_html(),
        file_name="esg_lite_report.html",
        mime="text/html"
    )
