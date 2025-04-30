import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import re

# -------- KONFIGURASI GOOGLE SHEET --------
SPREADSHEET_ID = "ISI_ID_SPREADSHEET_MU"
SHEET_NAME = "Sheet1"  # atau nama sheet yang kamu pakai
CREDENTIAL_PATH = "lian-408711-af0e2662b03d.json"

# -------- KONEKSI GOOGLE SHEETS --------
@st.cache_resource
def connect_to_gsheet():
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    credentials = Credentials.from_service_account_file(CREDENTIAL_PATH, scopes=scope)
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    return sheet

# -------- PARSING FUNGSI DARI TEKS --------
def parse_trading_summary(text):
    date_match = re.search(r"📅\s*(.+?)\s+Daily", text)
    date = date_match.group(1) if date_match else "Unknown"

    total_signals = int(re.search(r"Total Signals:\s*(\d+)", text).group(1))
    tp = int(re.search(r"Take-Profits:\s*(\d+)", text).group(1))
    sl = int(re.search(r"Stop-Losses:\s*(\d+)", text).group(1))
    finished = tp + sl
    winrate = round((tp / finished) * 100, 2) if finished > 0 else 0

    return {
        "Date": date,
        "Total_Signal": total_signals,
        "Finished": finished,
        "TP": tp,
        "SL": sl,
        "Winrate_pct": winrate,
    }

# -------- STREAMLIT UI --------
st.title("📊 Rekapan Hasil Trading Harian")

input_text = st.text_area("Masukkan teks rekap sinyal trading:", height=300)

if input_text and st.button("🔍 Proses dan Hitung"):
    result = parse_trading_summary(input_text)
    comment = st.text_input("Comment (opsional):", placeholder="Contoh: Good momentum, banyak TP")
    result["Comment"] = comment

    st.subheader("📋 Hasil Parsing:")
    st.write(result)

    if st.button("📤 Upload ke Google Sheets"):
        sheet = connect_to_gsheet()
        sheet.append_row([
            result["Date"],
            result["Total_Signal"],
            result["Finished"],
            result["TP"],
            result["SL"],
            f"{result['Winrate_pct']}%",
            result["Comment"]
        ])
        st.success("✅ Data berhasil ditambahkan ke Google Sheets!")
