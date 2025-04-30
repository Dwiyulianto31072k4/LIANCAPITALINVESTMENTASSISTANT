import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import re

# -------- KONFIGURASI GOOGLE SHEETS --------
SPREADSHEET_ID = "1g3XL1EllHoWV3jhmi7gT3at6MtCNTJBo8DQ1WyWhMEo"
SHEET_NAME = "Sheet1"

# -------- KONEKSI GOOGLE SHEETS --------
@st.cache_resource
def connect_to_gsheet():
    # Ambil dari secrets (sudah aman, tidak hardcode!)
    credentials_info = json.loads(st.secrets["credentials_json"])
    credentials = Credentials.from_service_account_info(
        credentials_info,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
    )
    client = gspread.authorize(credentials)
    sheet = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    return sheet

# -------- PARSING FUNGSI --------
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

# -------- UI STREAMLIT --------
st.title("📊 Rekapan Hasil Trading Harian")

if 'result' not in st.session_state:
    st.session_state.result = None
if 'upload_success' not in st.session_state:
    st.session_state.upload_success = False

# Input otomatis
input_text = st.text_area("Masukkan teks rekap sinyal trading:", height=300)
process_btn = st.button("🔍 Proses dan Hitung")

# Input manual
st.markdown("---")
st.subheader("Atau Input Manual")
col1, col2 = st.columns(2)
with col1:
    manual_date = st.text_input("Tanggal:", placeholder="Contoh: 28 April 2025")
    manual_total = st.number_input("Total Signal:", min_value=0, value=0)
    manual_tp = st.number_input("Take-Profits:", min_value=0, value=0)
with col2:
    manual_sl = st.number_input("Stop-Losses:", min_value=0, value=0)
    manual_comment = st.text_input("Comment:", placeholder="Contoh: Good momentum, banyak TP")

manual_btn = st.button("💾 Simpan Data Manual")

# Proses parsing otomatis
if process_btn and input_text:
    try:
        result = parse_trading_summary(input_text)
        st.session_state.result = result
        st.session_state.result["Comment"] = ""
    except Exception as e:
        st.error(f"❌ Error saat parsing: {str(e)}")

# Proses input manual
if manual_btn:
    if manual_date and manual_total >= 0 and manual_tp >= 0 and manual_sl >= 0:
        finished = manual_tp + manual_sl
        winrate = round((manual_tp / finished) * 100, 2) if finished > 0 else 0
        st.session_state.result = {
            "Date": manual_date,
            "Total_Signal": manual_total,
            "Finished": finished,
            "TP": manual_tp,
            "SL": manual_sl,
            "Winrate_pct": winrate,
            "Comment": manual_comment
        }
    else:
        st.warning("⚠️ Harap isi semua field dengan benar")

# Upload
if st.session_state.result:
    st.markdown("---")
    st.subheader("📋 Hasil Data:")
    
    if process_btn and input_text:
        st.session_state.result["Comment"] = st.text_input(
            "Comment (opsional):",
            placeholder="Contoh: Good momentum, banyak TP",
            value=st.session_state.result.get("Comment", "")
        )

    st.write(st.session_state.result)

    upload_btn = st.button("📤 Upload ke Google Sheets", key="upload_final")
    if upload_btn:
        try:
            sheet = connect_to_gsheet()
            sheet.append_row([
                st.session_state.result["Date"],
                st.session_state.result["Total_Signal"],
                st.session_state.result["Finished"],
                st.session_state.result["TP"],
                st.session_state.result["SL"],
                f"{st.session_state.result['Winrate_pct']}%",
                st.session_state.result["Comment"]
            ])
            st.success("✅ Data berhasil diupload ke Google Sheets!")
            st.markdown(f"[🔗 Lihat Spreadsheet](https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID})")
            st.session_state.upload_success = True
        except Exception as e:
            st.error(f"❌ Gagal upload: {str(e)}")

# Contoh input
with st.expander("ℹ️ Contoh Format Input"):
    st.markdown("""
    ```
    📅 18 April 2025 Daily Trading Report
    
    Total Signals: 15
    Take-Profits: 10
    Stop-Losses: 3
    ```
    """)

st.markdown("---")
st.markdown("Made with ❤️ by Lian Capital")
