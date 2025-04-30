import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import re
import os
from openai import OpenAI

# -------- KONFIGURASI GOOGLE SHEETS --------
SPREADSHEET_ID = "1g3XL1EllHoWV3jhmi7gT3at6MtCNTJBo8DQ1WyWhMEo"
SHEET_NAME = "Sheet1"

# -------- KONEKSI GOOGLE SHEETS --------
@st.cache_resource
def connect_to_gsheet():
    try:
        # Sesuaikan dengan nama kunci yang Anda gunakan di Streamlit Cloud
        if "gcp_service_account" in st.secrets:
            credentials_info = st.secrets["gcp_service_account"]
        elif "credentials_json" in st.secrets:
            if isinstance(st.secrets["credentials_json"], dict):
                credentials_info = st.secrets["credentials_json"]
            else:
                credentials_info = json.loads(st.secrets["credentials_json"])
        else:
            # Coba baca dari environment untuk development lokal
            credentials_json_str = os.environ.get("CREDENTIALS_JSON")
            if credentials_json_str:
                credentials_info = json.loads(credentials_json_str)
            else:
                raise ValueError("Kredensial Google Sheets tidak ditemukan. Pastikan secret 'gcp_service_account' atau 'credentials_json' sudah dikonfigurasi.")
        
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
    except Exception as e:
        st.error(f"Detail error koneksi Google Sheets: {str(e)}")
        raise e

# -------- KONEKSI OPENAI API --------
def get_openai_client():
    api_key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
    if not api_key:
        st.error("OpenAI API key tidak ditemukan!")
        return None
    return OpenAI(api_key=api_key)

# -------- FUNGSI AI KOMENTAR --------
def get_ai_trading_comment(data):
    client = get_openai_client()
    if not client:
        return "AI analisis tidak tersedia (API key tidak dikonfigurasi)"
    
    # Siapkan prompt untuk AI dengan data trading
    winrate = data["Winrate_pct"]
    tp = data["TP"]
    sl = data["SL"]
    completion_rate = (data["Finished"] / data["Total_Signal"] * 100) if data["Total_Signal"] > 0 else 0
    
    prompt = f"""
    Analisis data trading berikut dan berikan komentar profesional dalam Bahasa Indonesia (maksimal 80 kata):
    
    - Tanggal: {data['Date']}
    - Total Signal: {data['Total_Signal']}
    - Take-Profits: {tp}
    - Stop-Losses: {sl}
    - Finished: {data['Finished']}
    - Winrate: {winrate}%
    - Tingkat Penyelesaian: {completion_rate:.1f}%
    
    Berikan analisis yang tajam dan membantu para trader dengan memperhatikan:
    1. Kualitas performa trading (apakah winrate bagus atau kurang)
    2. Evaluasi rasio TP/SL dan signifikansinya
    3. Tingkat penyelesaian sinyal dan implikasinya
    4. Saran konkret untuk meningkatkan performa trading hari berikutnya
    5. Jika winrate di bawah 50%, berikan motivasi positif
    
    Komentar harus objektif, padat, dan langsung ke titik masalah.
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # atau "gpt-4" untuk hasil lebih baik
            messages=[
                {"role": "system", "content": "Kamu adalah analis trading profesional yang memberikan insight tajam, profesional dan bernilai tinggi. Kamu memahami berbagai strategi trading dan metrik kinerja."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error saat menghubungi AI: {str(e)}")
        return generate_backup_comment(data)  # Gunakan backup comment jika AI gagal

# -------- PARSING FUNGSI --------
def parse_trading_summary(text):
    try:
        date_match = re.search(r"📅\s*(.+?)\s+Daily", text)
        date = date_match.group(1) if date_match else "Unknown"

        total_signals_match = re.search(r"Total Signal[s]?:\s*(\d+)", text)
        if not total_signals_match:
            raise ValueError("Total Signal tidak ditemukan dalam teks")
        total_signals = int(total_signals_match.group(1))

        tp_match = re.search(r"Take[-\s]?Profit[s]?:\s*(\d+)", text)
        if not tp_match:
            raise ValueError("Take-Profit tidak ditemukan dalam teks")
        tp = int(tp_match.group(1))

        sl_match = re.search(r"Stop[-\s]?Loss(?:es)?:\s*(\d+)", text)
        if not sl_match:
            raise ValueError("Stop-Loss tidak ditemukan dalam teks")
        sl = int(sl_match.group(1))

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
    except Exception as e:
        raise ValueError(f"Format teks tidak valid: {str(e)}")

# -------- BACKUP KOMENTAR GENERATOR (FALLBACK) --------
def generate_backup_comment(data):
    """Menghasilkan komentar otomatis jika OpenAI API tidak tersedia."""
    winrate = data["Winrate_pct"]
    tp = data["TP"]
    sl = data["SL"]
    total = data["Total_Signal"]
    finished = data["Finished"]
    
    # Analisis winrate
    if winrate >= 80:
        performance = "Performa sangat baik dengan winrate tinggi"
    elif winrate >= 70:
        performance = "Performa baik dengan winrate solid"
    elif winrate >= 60:
        performance = "Performa cukup baik, masih di atas rata-rata market"
    elif winrate >= 50:
        performance = "Performa rata-rata, perlu ditingkatkan"
    else:
        performance = "Performa di bawah rata-rata, perlu evaluasi strategi"
    
    # Analisis rasio penyelesaian
    completion_rate = (finished / total) * 100 if total > 0 else 0
    if completion_rate >= 90:
        completion = "Tingkat eksekusi sinyal sangat baik"
    elif completion_rate >= 70:
        completion = "Tingkat eksekusi sinyal cukup baik"
    else:
        completion = "Perlu meningkatkan tingkat eksekusi sinyal"
    
    # Analisis rasio TP:SL
    if tp > sl and tp > 0:
        ratio = f"Rasio TP:SL positif {tp}:{sl} menunjukkan strategi efektif"
    elif tp == sl and tp > 0:
        ratio = f"Rasio TP:SL seimbang {tp}:{sl}, perlu ditingkatkan"
    elif tp > 0 and sl > 0:
        ratio = f"Rasio TP:SL negatif {tp}:{sl}, perlu perbaikan strategi"
    else:
        ratio = "Belum cukup data untuk analisis rasio TP:SL"
    
    # Rekomendasi
    if winrate >= 60:
        recommendation = "Pertahankan strategi dan tingkatkan volume trading secara bertahap."
    elif winrate >= 50:
        recommendation = "Evaluasi setup trading yang kurang optimal, fokus pada kualitas sinyal."
    else:
        recommendation = "Revisi strategi entry/exit dan atur ulang parameter risk management."
    
    # Gabungkan komentar
    comment = f"{performance}. {completion}. {ratio}. Rekomendasi: {recommendation}"
    return comment

# -------- UI STREAMLIT --------
st.set_page_config(
    page_title="Trading Report | Lian Capital",
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.title("📊 Rekapan Hasil Trading Harian")
st.markdown("Aplikasi sederhana untuk mencatat dan menganalisis performa trading harian Anda.")

if 'result' not in st.session_state:
    st.session_state.result = None
if 'upload_success' not in st.session_state:
    st.session_state.upload_success = False
if 'ai_comment_loading' not in st.session_state:
    st.session_state.ai_comment_loading = False

# Reset button (header)
if st.session_state.result and not st.session_state.ai_comment_loading:
    if st.button("🔄 Input Baru", key="reset_top"):
        st.session_state.result = None
        st.session_state.upload_success = False
        st.experimental_rerun()

# Contoh pesan untuk panduan format
if not st.session_state.result:
    st.info("""
    ℹ️ **Format Input:**
    ```
    📅 18 April 2025 Daily Trading Report
    
    Total Signals: 15
    Take-Profits: 10
    Stop-Losses: 3
    ```
    """)

# Area input teks
input_placeholder = """📅 DD Bulan YYYY Daily Trading Report

Total Signals: XX
Take-Profits: XX
Stop-Losses: XX"""

if not st.session_state.result:
    input_text = st.text_area(
        "Salin & tempel rekap trading Anda di sini:",
        placeholder=input_placeholder,
        height=200
    )
    
    col1, col2 = st.columns([1, 1])
    with col1:
        process_btn = st.button("🔍 Proses dan Hitung", use_container_width=True)
    with col2:
        clear_btn = st.button("🧹 Bersihkan", use_container_width=True)
        if clear_btn:
            st.experimental_rerun()

# Proses parsing otomatis
if process_btn and input_text:
    try:
        result = parse_trading_summary(input_text)
        st.session_state.result = result
        
        # Set flag untuk loading AI comment
        st.session_state.ai_comment_loading = True
        st.experimental_rerun()
        
    except Exception as e:
        st.error(f"❌ Error saat parsing: {str(e)}")
        st.markdown("""
        **Pastikan format sesuai contoh:**
        ```
        📅 Tanggal Daily Trading Report
        
        Total Signals: [Angka]
        Take-Profits: [Angka]
        Stop-Losses: [Angka]
        ```
        """)

# Proses loading AI comment jika diperlukan
if st.session_state.ai_comment_loading and st.session_state.result:
    with st.spinner("Mendapatkan analisis AI..."):
        try:
            ai_comment = get_ai_trading_comment(st.session_state.result)
            st.session_state.result["Comment"] = ai_comment
        except Exception as e:
            st.warning(f"⚠️ Tidak dapat menggunakan AI, menggunakan analisis backup: {str(e)}")
            backup_comment = generate_backup_comment(st.session_state.result)
            st.session_state.result["Comment"] = backup_comment
        
        st.session_state.ai_comment_loading = False
        st.experimental_rerun()

# Tampilkan hasil
if st.session_state.result and not st.session_state.ai_comment_loading:
    st.markdown("---")
    st.subheader("📋 Hasil Analisis:")
    
    # Buat kartu metrik dengan gaya yang lebih baik
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Signal", st.session_state.result["Total_Signal"])
    with col2:
        st.metric("Take-Profits", st.session_state.result["TP"])
    with col3:
        st.metric("Stop-Losses", st.session_state.result["SL"])
    
    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric("Tanggal", st.session_state.result["Date"])
    with col5:
        st.metric("Finished", st.session_state.result["Finished"])
    with col6:
        # Warna berdasarkan winrate
        winrate = st.session_state.result["Winrate_pct"]
        delta_color = "normal"
        if winrate >= 70:
            delta_color = "good"
        elif winrate < 50:
            delta_color = "inverse"
        st.metric("Winrate", f"{winrate}%", delta=f"{winrate-50:+.1f}% dari 50%", delta_color=delta_color)

    # Tampilkan komentar AI
    st.subheader("💡 Analisis Trading:")
    st.info(st.session_state.result.get("Comment", ""))
    
    # Edit komentar AI jika perlu
    edited_comment = st.text_area(
        "Edit analisis jika diperlukan:",
        value=st.session_state.result.get("Comment", ""),
        height=100
    )
    st.session_state.result["Comment"] = edited_comment

    # Tombol upload final
    col_back, col_upload = st.columns([1, 2])
    
    with col_back:
        if st.button("« Kembali", use_container_width=True):
            st.session_state.result = None
            st.experimental_rerun()
    
    with col_upload:
        upload_btn = st.button("📤 Simpan ke Google Sheets", key="upload_final", use_container_width=True)
    
    if upload_btn:
        try:
            with st.spinner("Menyimpan data..."):
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
            st.success("✅ Data berhasil disimpan ke Google Sheets!")
            st.balloons()
            
            # Tampilkan link ke spreadsheet
            st.markdown(f"[🔗 Lihat Spreadsheet](https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID})")
            
            # Reset status dan tampilkan tombol untuk data baru
            st.session_state.upload_success = True
            
            if st.button("➕ Tambah Data Baru", key="add_new"):
                st.session_state.result = None
                st.session_state.upload_success = False
                st.experimental_rerun()
                
        except Exception as e:
            st.error(f"❌ Gagal upload: {str(e)}")

# Tampilkan statistik historis dalam expander
with st.expander("📈 Statistik Trading (7 Hari Terakhir)"):
    if st.button("🔄 Muat Statistik"):
        try:
            import pandas as pd
            import matplotlib.pyplot as plt
            import altair as alt
            from datetime import datetime, timedelta
            
            sheet = connect_to_gsheet()
            
            # Ambil semua data
            data = sheet.get_all_records()
            
            if data:
                df = pd.DataFrame(data)
                
                # Konversi winrate dari string ke numerik
                if 'Winrate' in df.columns:
                    df['Winrate_num'] = df['Winrate'].str.rstrip('%').astype(float)
                
                # Tunjukkan hanya 7 data terakhir
                df_recent = df.tail(7)
                
                # Buat chart dengan Altair
                if len(df_recent) > 0:
                    # Winrate Chart
                    st.write("### Winrate 7 Hari Terakhir")
                    chart_winrate = alt.Chart(df_recent).mark_line(point=True).encode(
                        x=alt.X('Date:N', title='Tanggal', sort=None),
                        y=alt.Y('Winrate_num:Q', title='Winrate (%)', scale=alt.Scale(domain=[0, 100])),
                        tooltip=['Date', 'Winrate', 'Total_Signal', 'TP', 'SL']
                    ).properties(height=250)
                    st.altair_chart(chart_winrate, use_container_width=True)
                    
                    # TP/SL Chart
                    st.write("### Perbandingan TP vs SL")
                    df_melted = pd.melt(df_recent, id_vars=['Date'], value_vars=['TP', 'SL'], 
                                      var_name='Type', value_name='Count')
                    
                    chart_tpsl = alt.Chart(df_melted).mark_bar().encode(
                        x=alt.X('Date:N', title='Tanggal'),
                        y=alt.Y('Count:Q', title='Jumlah'),
                        color=alt.Color('Type:N', scale=alt.Scale(
                            domain=['TP', 'SL'],
                            range=['#36b37e', '#ff5630']
                        )),
                        tooltip=['Date', 'Type', 'Count']
                    ).properties(height=250)
                    st.altair_chart(chart_tpsl, use_container_width=True)
                    
                    # Ringkasan statistik
                    st.write("### Ringkasan Statistik")
                    avg_winrate = df_recent['Winrate_num'].mean()
                    total_tp = df_recent['TP'].sum()
                    total_sl = df_recent['SL'].sum() 
                    total_signals = df_recent['Total_Signal'].sum()
                    
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Rata-rata Winrate", f"{avg_winrate:.1f}%")
                    col2.metric("Total TP", total_tp)
                    col3.metric("Total SL", total_sl)
                    
                    # Baris kedua
                    col4, col5, col6 = st.columns(3)
                    col4.metric("Total Signals", total_signals)
                    
                    if total_tp + total_sl > 0:
                        overall_winrate = (total_tp / (total_tp + total_sl)) * 100
                        col5.metric("Overall Winrate", f"{overall_winrate:.1f}%")
                    
                    completion_rate = ((total_tp + total_sl) / total_signals) * 100 if total_signals > 0 else 0
                    col6.metric("Completion Rate", f"{completion_rate:.1f}%")
                    
                    # Data lengkap
                    st.write("### Data 7 Hari Terakhir")
                    st.dataframe(df_recent[['Date', 'Total_Signal', 'TP', 'SL', 'Winrate']], use_container_width=True)
                else:
                    st.info("Belum ada data yang cukup untuk ditampilkan")
            else:
                st.info("Belum ada data yang tersimpan dalam Google Sheets")
        except Exception as e:
            st.error(f"Gagal memuat statistik: {str(e)}")

# Tambahkan petunjuk konfigurasi
with st.expander("🔧 Konfigurasi"):
    st.markdown("""
    ### Konfigurasi API Key dan Google Service Account
    
    Untuk konfigurasi yang benar, tambahkan secrets berikut ke Streamlit Cloud:
    
    1. `OPENAI_API_KEY` - untuk generate komentar AI
    2. `gcp_service_account` - untuk akses Google Sheets
    
    Format TOML yang benar:
    ```toml
    OPENAI_API_KEY = "sk-your-api-key"
    
    [gcp_service_account]
    type = "service_account"
    project_id = "your-project-id"
    private_key_id = "your-key-id"
    private_key = "-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n"
    client_email = "your-service-account@your-project.iam.gserviceaccount.com"
    client_id = "your-client-id"
    auth_uri = "https://accounts.google.com/o/oauth2/auth"
    token_uri = "https://oauth2.googleapis.com/token"
    auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
    client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account"
    universe_domain = "googleapis.com"
    ```
    """)

st.markdown("---")
st.markdown("<div style='text-align: center'>Made with ❤️ by Lian Capital</div>", unsafe_allow_html=True)
