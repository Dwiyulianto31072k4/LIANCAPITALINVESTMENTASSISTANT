import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import re
import json

# -------- KONFIGURASI GOOGLE SHEET --------
SPREADSHEET_ID = "1g3XL1EllHoWV3jhmi7gT3at6MtCNTJBo8DQ1WyWhMEo"
SHEET_NAME = "Sheet1"  # atau nama sheet yang kamu pakai

# -------- KONEKSI GOOGLE SHEETS --------
@st.cache_resource
def connect_to_gsheet():
    # Cek apakah credentials tersedia di secrets
    if 'gcp_credentials' in st.secrets:
        # Untuk deployment di Streamlit Cloud
        credentials_info = st.secrets["gcp_credentials"]
        credentials = Credentials.from_service_account_info(
            credentials_info,
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
    else:
        # Untuk development lokal
        CREDENTIAL_PATH = "lian-408711-fe452dc9b79f.json"  # File json kredensial lokal
        credentials = Credentials.from_service_account_file(
            CREDENTIAL_PATH, 
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
    
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
    try:
        result = parse_trading_summary(input_text)
        comment = st.text_input("Comment (opsional):", placeholder="Contoh: Good momentum, banyak TP")
        result["Comment"] = comment

        st.subheader("📋 Hasil Parsing:")
        st.write(result)

        if st.button("📤 Upload ke Google Sheets"):
            try:
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
            except Exception as e:
                st.error(f"❌ Error saat mengupload ke Google Sheets: {str(e)}")
                st.info("Pastikan service account memiliki akses ke spreadsheet dan ID spreadsheet sudah benar.")
    except Exception as e:
        st.error(f"❌ Error saat memproses teks: {str(e)}")
        st.info("Pastikan format teks sesuai dengan yang diharapkan.")

# Tampilkan contoh format input
with st.expander("ℹ️ Contoh Format Input"):
    st.markdown("""
    ```
    📅 18 April 2025 Daily Trading Report
    
    Total Signals: 15
    Take-Profits: 10
    Stop-Losses: 3
    ```
    """)

# Menambahkan footer
st.markdown("---")
st.markdown("Made with ❤️ by Lian Capital")
