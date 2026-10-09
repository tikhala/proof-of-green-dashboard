from datetime import datetime
from html import escape

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pytz
import streamlit as st

st.set_page_config(page_title="Proof of Green — Cirata Solar", layout="wide")
st.title("🔆 Proof of Green: Cirata Floating Solar Digital Twin")
st.caption(
    "Showcase project. Generation is modelled from public weather data (Open-Meteo) and checked against "
    "NASA POWER. It is not metered output from the plant, and the NFTs are on the Polygon Amoy test network."
)

DATA_REPO = "https://raw.githubusercontent.com/tikhala/proof-of-green-data/main"
VALIDATED_URL = f"{DATA_REPO}/validated_data.csv"
NFT_LEDGER_URL = f"{DATA_REPO}/nft_ledger.csv"
EXPLORER_TX = "https://amoy.polygonscan.com/tx/"
EMISSION_FACTOR_KG_PER_KWH = 0.793   # Indonesia grid average


@st.cache_data(ttl=300)
def load_data(url):
    try:
        return pd.read_csv(url, parse_dates=["timestamp"])
    except Exception:
        return pd.DataFrame()


validated = load_data(VALIDATED_URL)
nft_ledger = load_data(NFT_LEDGER_URL)

if validated.empty:
    st.warning("No data found yet. The pipeline has not published results.")
    st.stop()

jakarta = pytz.timezone("Asia/Jakarta")
now = datetime.now(jakarta)
st.caption(f"Page loaded: {now.strftime('%Y-%m-%d %H:%M WIB')} | Data refreshes daily (source data lags by a few days)")

# ---------------------------------------------------------------- derived data
validated["date"] = validated["timestamp"].dt.floor("D")
daily = validated.groupby("date").agg(
    twin_kwh=("twin_generation_kwh", "sum"),
    nasa_kwh=("nasa_expected_kwh", "sum"),
    status=("status", "first"),
).reset_index()
daily["twin_mwh"] = daily["twin_kwh"] / 1000
daily["nasa_mwh"] = daily["nasa_kwh"] / 1000

verified_mwh = float(validated["cumulative_verified_energy_mwh"].max())
co2_tonnes = verified_mwh * EMISSION_FACTOR_KG_PER_KWH     # MWh x 0.793 t/MWh
minted = len(nft_ledger) if not nft_ledger.empty else 0
data_through = validated["timestamp"].max()

weather = validated.dropna(subset=["cloud_cover_percent", "humidity_percent"])
latest = weather.iloc[-1] if not weather.empty else None

# ---------------------------------------------------------------- KPIs
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Minted NFTs", minted)
c2.metric("CO₂ avoided (t, verified)", f"{co2_tonnes:,.0f}")
c3.metric("Plant capacity", "192 MWp / 145 MWac")
c4.metric("Data through", data_through.strftime("%d %b %Y"))
c5.metric("Cloud cover", f"{latest['cloud_cover_percent']:.0f}%" if latest is not None else "n/a")
c6.metric("Humidity", f"{latest['humidity_percent']:.0f}%" if latest is not None else "n/a")

st.markdown("---")

# ---------------------------------------------------------------- main chart (daily)
st.subheader("Digital twin vs NASA POWER (daily energy)")
fig = go.Figure()
fig.add_trace(go.Scatter(x=daily["date"], y=daily["twin_mwh"], mode="lines",
                         name="Digital twin (Open-Meteo + PV model)", line=dict(color="blue", width=1)))
fig.add_trace(go.Scatter(x=daily["date"], y=daily["nasa_mwh"], mode="lines",
                         name="NASA POWER expected", line=dict(color="orange", width=1)))
bad = daily[daily["status"] == "INVALID"]
fig.add_trace(go.Scatter(x=bad["date"], y=bad["twin_mwh"], mode="markers",
                         name="Invalid day", marker=dict(color="red", size=4)))
fig.update_layout(height=450, margin=dict(l=0, r=0, t=30, b=0), yaxis_title="MWh per day",
                  legend=dict(orientation="h", yanchor="bottom", y=1.02))
st.plotly_chart(fig, use_container_width=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Cumulative Energy", "NFT Activity", "Monthly Summary", "Validation Pass Rate", "ESG-Lite Report"
])

with tab1:
    st.subheader("Cumulative verified energy")
    fig = px.area(validated, x="timestamp", y="cumulative_verified_energy_mwh", title="Verified energy (MWh)")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.subheader("Recent NFT mints")
    if not nft_ledger.empty:
        ledger = nft_ledger.copy()
        if "nft_type" in ledger.columns:
            ledger["type_label"] = ledger["nft_type"].replace({
                "historical_quarterly": "📅 Quarterly",
                "forward_50gwh": "⚡ 50 GWh milestone",
            })
        if "tx_hash" in ledger.columns:
            ledger["explorer"] = EXPLORER_TX + ledger["tx_hash"].astype(str)
        wanted = ["token_id", "type_label", "energy_mwh", "co2_kg", "explorer", "timestamp"]
        cols = [c for c in wanted if c in ledger.columns]
        st.dataframe(
            ledger[cols].tail(20),
            hide_index=True,
            column_config={"explorer": st.column_config.LinkColumn("Transaction", display_text="View")},
        )
    else:
        st.info("No NFTs minted yet.")

with tab3:
    st.subheader("Monthly energy generation")
    monthly_src = validated.set_index("timestamp")[["twin_generation_kwh"]]
    try:
        monthly = monthly_src.resample("ME").sum()
    except ValueError:          # older pandas
        monthly = monthly_src.resample("M").sum()
    monthly["month"] = monthly.index.strftime("%b %Y")
    monthly["twin_mwh"] = monthly["twin_generation_kwh"] / 1000
    fig = px.bar(monthly, x="month", y="twin_mwh", title="Monthly generation (MWh)")
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.subheader("Validation pass rate (per day)")
    total = len(daily)
    valid_days = int((daily["status"] == "VALID").sum())
    invalid_days = total - valid_days
    st.write(f"Valid days: {valid_days} ({valid_days / total:.1%})")
    st.write(f"Invalid days: {invalid_days} ({invalid_days / total:.1%})")
    fig = px.pie(values=[valid_days, invalid_days], names=["Valid", "Invalid"],
                 title="Daily validation status")
    st.plotly_chart(fig, use_container_width=True)


def build_report_html():
    rows = [
        ("Period", f"{validated['timestamp'].min():%d %b %Y} to {data_through:%d %b %Y}"),
        ("Total twin generation", f"{validated['twin_generation_kwh'].sum():,.0f} kWh"),
        ("Total NASA-expected generation", f"{validated['nasa_expected_kwh'].sum():,.0f} kWh"),
        ("Total verified energy", f"{verified_mwh:,.0f} MWh"),
        ("NFTs minted", str(minted)),
        ("Assumed CO₂ offset (verified energy)", f"{co2_tonnes:,.0f} tonnes"),
        ("Assumed emission factor", f"{EMISSION_FACTOR_KG_PER_KWH} kg CO₂/kWh (Indonesia grid average)"),
    ]
    body = "".join(f"<tr><td>{escape(k)}</td><td>{escape(v)}</td></tr>" for k, v in rows)
    return (
        "<html><head><meta charset='utf-8'><title>Proof of Green ESG-Lite Report</title></head><body>"
        "<h1>Cirata Floating Solar — Proof of Green</h1>"
        "<p><em>Non-audited. Generation is modelled from public weather data, not metered.</em></p>"
        f"<table border='1' cellpadding='6'>{body}</table>"
        "<p>Data: Open-Meteo, NASA POWER.</p></body></html>"
    )


with tab5:
    st.subheader("ESG-Lite / non-audited report")
    st.markdown("**Cirata Floating Solar Plant — Proof of Green**")
    st.write(f"Period: {validated['timestamp'].min():%d %b %Y} to {data_through:%d %b %Y}")
    st.write(f"Total twin generation: {validated['twin_generation_kwh'].sum():,.0f} kWh")
    st.write(f"Total NASA-expected generation: {validated['nasa_expected_kwh'].sum():,.0f} kWh")
    st.write(f"Total verified energy: {verified_mwh:,.0f} MWh")
    st.write(f"NFTs minted: {minted}")
    st.write(f"Assumed CO₂ offset: {co2_tonnes:,.0f} tonnes")
    st.write(f"Assumed emission factor: {EMISSION_FACTOR_KG_PER_KWH} kg CO₂/kWh (Indonesia grid average)")
    st.download_button(
        "Download report (HTML)",
        data=build_report_html(),
        file_name="esg_lite_report.html",
        mime="text/html",
    )

st.markdown("---")
st.caption("Data: Open-Meteo (ERA5-based historical weather) and NASA POWER.")
