import re, datetime as dt
import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Konfigurasi Google Sheets
default_sheet_id = "1g3XL1EllHoWV3jhmi7gT3at6MtCNTJBo8DQ1WyWhMEo"
default_worksheet = "Tabel1"
json_keyfile = "lian-408711-8736ae6e6b31.json"  # ganti sesuai nama file JSON Anda

@st.cache_resource
def connect_sheet(sheet_id=default_sheet_id, worksheet=default_worksheet):
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile, scope)
    client = gspread.authorize(creds)
    return client.open_by_key(sheet_id).worksheet(worksheet)

# Fungsi parsing laporan harian def parse_report(text: str) -> dict:
    """Ekstrak Total, TP, SL, dan hitung win-rate."""
    get_int = lambda pat: int(re.search(pat, text, re.I).group(1))
    total = get_int(r"Total Signals:\s*(\d+)")
    tp    = get_int(r"Take-Profits:\s*(\d+)")
    sl    = get_int(r"Stop-Losses:\s*(\d+)")
    finished = tp + sl
    winrate = round(tp / finished * 100, 2) if finished else 0.0

    m = re.search(r"(\d{2})/(\d{2})-\d{2}/(\d{2})", text)
    if m:
        month, _, day_end = map(int, m.groups())
        year = dt.date.today().year
        date = dt.date(year, month, day_end)
    else:
        date = dt.date.today()

    return {
        "Date": date.isoformat(),
        "Total_Signal": total,
        "Finished": finished,
        "TP": tp,
        "SL": sl,
        "Winrate_pct": winrate,
        "Comment": ""
    }

st.title("🟢 Daily Crypto Signal Recorder")
ws = connect_sheet()
raw = st.text_area("Paste laporan harian di sini", height=300, placeholder="📅 04/28-04/29 Daily Results ...")

if st.button("Parse & Simpan"):
    if not raw.strip():
        st.warning("Input kosong, silakan paste laporan Anda.")
    else:
        try:
            record = parse_report(raw)
            ws.append_row(list(record.values()))
            st.success("✅ Data berhasil disimpan ke Google Sheets.")
            st.json(record)
        except Exception as e:
            st.error(f"Gagal parsing atau menyimpan: {e}")

st.divider()
# Tampilkan tabel rekap
df = pd.DataFrame(ws.get_all_records())
st.subheader("📊 Rekap Harian")
st.dataframe(df, use_container_width=True)
