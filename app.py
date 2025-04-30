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
    # Menggunakan variabel credentials_json dari secrets
    if 'credentials_json' in st.secrets:
        # Parse JSON string dari secrets
        try:
            credentials_info = json.loads(st.secrets["credentials_json"])
            credentials = Credentials.from_service_account_info(
                credentials_info,
                scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            )
        except Exception as e:
            st.error(f"Error parsing credentials_json: {str(e)}")
            st.stop()
    else:
        st.error("Tidak menemukan credentials_json di secrets!")
        st.stop()
    
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

# Inisialisasi state
if 'result' not in st.session_state:
    st.session_state.result = None
if 'upload_success' not in st.session_state:
    st.session_state.upload_success = False

# Mode input otomatis
input_text = st.text_area("Masukkan teks rekap sinyal trading:", height=300)
process_btn = st.button("🔍 Proses dan Hitung")

# Mode input manual (jika parsing gagal)
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

# Proses data otomatis
if process_btn and input_text:
    try:
        result = parse_trading_summary(input_text)
        if result:
            st.session_state.result = result
            st.session_state.result["Comment"] = ""  # Initialize empty comment
    except Exception as e:
        st.error(f"❌ Error saat memproses teks: {str(e)}")
        st.info("Pastikan format teks sesuai dengan yang diharapkan.")
        
# Proses data manual
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

# Tampilkan hasil dan opsi upload
if st.session_state.result:
    st.markdown("---")
    st.subheader("📋 Hasil Data:")
    
    # Tambahkan kolom comment jika dari parsing otomatis
    if process_btn and input_text:
        st.session_state.result["Comment"] = st.text_input("Comment (opsional):", 
                                                          placeholder="Contoh: Good momentum, banyak TP",
                                                          value=st.session_state.result.get("Comment", ""))
    
    st.write(st.session_state.result)
    
    # Tombol upload terpisah
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
            st.success("✅ Data berhasil ditambahkan ke Google Sheets!")
            st.markdown(f"[Lihat data di spreadsheet](https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID})")
            st.session_state.upload_success = True
        except Exception as e:
            st.error(f"❌ Error saat mengupload ke Google Sheets: {str(e)}")
            st.info("Pastikan service account memiliki akses ke spreadsheet dan ID spreadsheet sudah benar.")

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
