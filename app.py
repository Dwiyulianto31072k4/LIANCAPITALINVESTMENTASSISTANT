import os
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
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]
        
        # Coba menggunakan file JSON
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(json_keyfile, scope)
        except Exception as json_error:
            st.warning(f"Gagal membaca file JSON: {str(json_error)}")
            st.info("Mencoba metode alternatif...")
            
            # Jika file JSON tidak dapat diakses, coba gunakan alternatif (jika tersedia)
            try:
                # Alternatif 1: Periksa apakah ada environment variable
                if os.environ.get('GOOGLE_APPLICATION_CREDENTIALS'):
                    creds = ServiceAccountCredentials.from_json_keyfile_name(
                        os.environ['GOOGLE_APPLICATION_CREDENTIALS'], scope)
                # Alternatif 2: Coba gunakan Streamlit secrets jika tersedia
                elif 'gcp_service_account' in st.secrets:
                    import json
                    creds_dict = st.secrets["gcp_service_account"]
                    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
                else:
                    raise Exception("Tidak ada metode autentikasi alternatif yang tersedia")
            except Exception as alt_error:
                st.error(f"Semua metode autentikasi gagal: {str(alt_error)}")
                return None
        
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_id).worksheet(worksheet)
        
        # Uji koneksi dengan mencoba mendapatkan data
        sheet.cell(1, 1).value
        
        st.success("✅ Berhasil terhubung ke Google Sheets!")
        return sheet
    
    except gspread.exceptions.SpreadsheetNotFound:
        st.error(f"Spreadsheet dengan ID {sheet_id} tidak ditemukan. Pastikan ID benar dan service account memiliki akses.")
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Worksheet '{worksheet}' tidak ditemukan. Pastikan nama worksheet benar.")
    except gspread.exceptions.APIError as api_error:
        st.error(f"Google API Error: {str(api_error)}")
        st.info("Pastikan service account memiliki izin untuk mengakses spreadsheet ini.")
    except Exception as e:
        st.error(f"Error tidak terduga: {type(e).__name__}: {str(e)}")
    
    return None

# Fungsi parsing laporan harian
def parse_report(text: str) -> dict:
    """Ekstrak Total, TP, SL, dan hitung win-rate."""
    try:
        # Fungsi untuk mengekstrak angka dari pola teks
        def get_int(pat):
            match = re.search(pat, text, re.I)
            if not match:
                raise ValueError(f"Pola '{pat}' tidak ditemukan dalam teks")
            return int(match.group(1))
        
        total = get_int(r"Total Signals:\s*(\d+)")
        tp = get_int(r"Take-Profits:\s*(\d+)")
        sl = get_int(r"Stop-Losses:\s*(\d+)")
        
        finished = tp + sl
        winrate = round(tp / finished * 100, 2) if finished else 0.0

        # Ekstrak tanggal
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
    except Exception as e:
        raise ValueError(f"Gagal parsing laporan: {str(e)}")

# Aplikasi Streamlit 
st.title("🟢 Daily Crypto Signal Recorder")

# Tambah info debugging untuk kredensial
if st.sidebar.checkbox("Mode Debug", False):
    st.sidebar.info(f"File JSON path: {os.path.abspath(json_keyfile)}")
    st.sidebar.info(f"File exists: {os.path.exists(json_keyfile)}")
    st.sidebar.info(f"Current directory: {os.getcwd()}")
    st.sidebar.info(f"Files in directory: {', '.join(os.listdir())}")

# Coba hubungkan ke Google Sheets
ws = connect_sheet()

if ws is not None:
    # Input area
    raw = st.text_area("Paste laporan harian di sini", height=300, 
                       placeholder="📅 04/28-04/29 Daily Results ...\nTotal Signals: 10\nTake-Profits: 7\nStop-Losses: 3")

    col1, col2 = st.columns([1, 3])
    with col1:
        submit_button = st.button("Parse & Simpan", type="primary")
    
    with col2:
        preview_button = st.button("Preview (Tanpa Simpan)")

    # Process input
    if submit_button or preview_button:
        if not raw.strip():
            st.warning("⚠️ Input kosong, silakan paste laporan Anda.")
        else:
            try:
                record = parse_report(raw)
                
                if preview_button:
                    st.info("ℹ️ Preview data (belum disimpan):")
                    st.json(record)
                
                if submit_button:
                    ws.append_row(list(record.values()))
                    st.success("✅ Data berhasil disimpan ke Google Sheets.")
                    st.json(record)
            except Exception as e:
                st.error(f"❌ Gagal memproses data: {str(e)}")
                st.info("Pastikan format laporan sesuai contoh di placeholder.")

    st.divider()
    
    # Tampilkan tabel rekap jika worksheet tersedia
    try:
        with st.spinner("Mengambil data..."):
            records = ws.get_all_records()
            if records:
                df = pd.DataFrame(records)
                
                # Konversi tanggal jika ada
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date']).dt.date
                
                st.subheader("📊 Rekap Harian")
                st.dataframe(df, use_container_width=True)
                
                # Tambahkan ringkasan statistik
                if len(df) > 0:
                    st.subheader("📈 Statistik")
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Total Signals", df['Total_Signal'].sum())
                    with col2:
                        st.metric("Win Rate Rata-rata", f"{df['Winrate_pct'].mean():.2f}%")
                    with col3:
                        st.metric("Total Trading Days", len(df))
            else:
                st.info("Belum ada data dalam spreadsheet.")
    except Exception as e:
        st.error(f"Gagal mengambil data: {str(e)}")

else:
    st.error("❌ Tidak dapat terhubung ke Google Sheets.")
    st.warning("""
    Silakan periksa beberapa hal berikut:
    1. Pastikan file JSON kredensial valid dan berada di direktori yang sama dengan app.py
    2. Pastikan service account memiliki akses ke spreadsheet yang dituju
    3. Periksa apakah ID spreadsheet dan nama worksheet sudah benar
    
    Jika masalah berlanjut, silakan regenerate kredensial service account dari Google Cloud Console.
    """)
    
    # Tampilkan form dummy untuk demo
    st.info("Mode Demo (Tanpa koneksi ke Google Sheets)")
    raw = st.text_area("Contoh Laporan", height=300, value="""📅 04/28-04/29 Daily Results
Total Signals: 10
Take-Profits: 7
Stop-Losses: 3""")
    
    if st.button("Demo Parse"):
        try:
            record = parse_report(raw)
            st.json(record)
        except Exception as e:
            st.error(f"Gagal parsing: {str(e)}")
            
