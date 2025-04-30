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
st.title("📊 Rekapan Hasil Trading Harian")

if 'result' not in st.session_state:
    st.session_state.result = None
if 'upload_success' not in st.session_state:
    st.session_state.upload_success = False
if 'ai_comment_loading' not in st.session_state:
    st.session_state.ai_comment_loading = False

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
    manual_comment = st.text_input("Comment (opsional):", placeholder="Kosongkan untuk menggunakan AI")

manual_btn = st.button("💾 Simpan Data Manual")

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

# Proses input manual
if manual_btn:
    if manual_date and manual_total >= 0 and manual_tp >= 0 and manual_sl >= 0:
        finished = manual_tp + manual_sl
        winrate = round((manual_tp / finished) * 100, 2) if finished > 0 else 0
        result_data = {
            "Date": manual_date,
            "Total_Signal": manual_total,
            "Finished": finished,
            "TP": manual_tp,
            "SL": manual_sl,
            "Winrate_pct": winrate,
        }
        
        # Gunakan komentar manual jika disediakan
        if manual_comment:
            result_data["Comment"] = manual_comment
            st.session_state.result = result_data
        else:
            # Set untuk mendapatkan AI comment
            st.session_state.result = result_data
            st.session_state.ai_comment_loading = True
            st.experimental_rerun()
    else:
        st.warning("⚠️ Harap isi semua field dengan benar")

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

# Upload
if st.session_state.result and not st.session_state.ai_comment_loading:
    st.markdown("---")
    st.subheader("📋 Hasil Data:")
    
    # Tampilkan data dan beri opsi untuk mengedit komentar
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Signal", st.session_state.result["Total_Signal"])
        st.metric("Take-Profits", st.session_state.result["TP"])
        st.metric("Stop-Losses", st.session_state.result["SL"])
    with col2:
        st.metric("Tanggal", st.session_state.result["Date"])
        st.metric("Finished", st.session_state.result["Finished"])
        st.metric("Winrate", f"{st.session_state.result['Winrate_pct']}%")

    # Edit komentar AI
    st.subheader("Komentar AI Trading:")
    st.info(st.session_state.result.get("Comment", ""))
    edited_comment = st.text_area(
        "Edit komentar jika diperlukan:",
        value=st.session_state.result.get("Comment", ""),
        height=100
    )
    st.session_state.result["Comment"] = edited_comment

    # Tombol upload final
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
            st.balloons()
            st.markdown(f"[🔗 Lihat Spreadsheet](https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID})")
            st.session_state.upload_success = True
            
            # Reset hasil setelah upload berhasil
            if st.session_state.upload_success:
                if st.button("➕ Tambah Data Baru"):
                    st.session_state.result = None
                    st.session_state.upload_success = False
                    st.experimental_rerun()
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

# Tambahkan petunjuk konfigurasi
with st.expander("🔧 Konfigurasi"):
    st.markdown("""
    ### Konfigurasi API Key dan Google Service Account
    
    Untuk konfigurasi yang benar, tambahkan secrets berikut ke Streamlit Cloud:
    
    1. `OPENAI_API_KEY` = "api-key-anda"
    2. `gcp_service_account` = {...} (objek JSON credential Google Service Account)
    
    Atau tambahkan sebagai environment variable pada deployment lokal.
    """)

# Tampilkan statistik historis jika tersedia
with st.expander("📈 Statistik Trading (7 Hari Terakhir)"):
    st.info("Untuk melihat statistik historis, pastikan Anda telah mengupload data sebelumnya.")
    if st.button("🔄 Muat Statistik"):
        try:
            sheet = connect_to_gsheet()
            # Ambil 7 data terakhir
            data = sheet.get_all_records()[-7:]
            if data:
                import pandas as pd
                import altair as alt
                
                df = pd.DataFrame(data)
                
                # Konversi winrate dari string ke numerik jika perlu
                if 'Winrate' in df.columns:
                    df['Winrate_num'] = df['Winrate'].str.rstrip('%').astype(float)
                
                # Buat chart
                if len(df) > 0:
                    st.write("### Winrate 7 Hari Terakhir")
                    chart = alt.Chart(df).mark_line().encode(
                        x=alt.X('Date:N', title='Tanggal'),
                        y=alt.Y('Winrate_num:Q', title='Winrate (%)')
                    ).properties(height=200)
                    st.altair_chart(chart, use_container_width=True)
                    
                    st.write("### Data Lengkap")
                    st.dataframe(df)
                else:
                    st.write("Belum ada data yang cukup untuk ditampilkan")
            else:
                st.write("Belum ada data yang tersimpan")
        except Exception as e:
            st.error(f"Gagal memuat statistik: {str(e)}")

st.markdown("---")
st.markdown("Made with ❤️ by Lian Capital")
