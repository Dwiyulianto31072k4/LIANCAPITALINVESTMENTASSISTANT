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

# -------- LANGUAGE SETTINGS --------
# Dictionary with text in multiple languages (Indonesian and English for now)
LANGUAGES = {
    "id": {
        "page_title": "Trading Report | Lian Capital",
        "main_title": "📊 Rekapan Hasil Trading Harian",
        "app_description": "Aplikasi sederhana untuk mencatat dan menganalisis performa trading harian Anda.",
        "input_format_info": """
        ℹ️ **Format Input:**
        ```
        📅 18 April 2025 Daily Trading Report
        
        Total Signals: 15
        Take-Profits: 10
        Stop-Losses: 3
        ```
        """,
        "input_placeholder": """📅 DD Bulan YYYY Daily Trading Report

Total Signals: XX
Take-Profits: XX
Stop-Losses: XX""",
        "input_label": "Salin & tempel rekap trading Anda di sini:",
        "process_button": "🔍 Proses dan Hitung",
        "clear_button": "🧹 Bersihkan",
        "new_input_button": "🔄 Input Baru",
        "parsing_error": "❌ Error saat parsing: ",
        "format_reminder": """
        **Pastikan format sesuai contoh:**
        ```
        📅 Tanggal Daily Trading Report
        
        Total Signals: [Angka]
        Take-Profits: [Angka]
        Stop-Losses: [Angka]
        ```
        """,
        "loading_ai": "Mendapatkan analisis AI...",
        "ai_error": "⚠️ Tidak dapat menggunakan AI, menggunakan analisis backup: ",
        "results_header": "📋 Hasil Analisis:",
        "total_signal": "Total Signal",
        "take_profits": "Take-Profits",
        "stop_losses": "Stop-Losses",
        "date": "Tanggal",
        "finished": "Finished",
        "winrate": "Winrate",
        "analysis_header": "💡 Analisis Trading:",
        "edit_analysis": "Edit analisis jika diperlukan:",
        "back_button": "« Kembali",
        "save_button": "📤 Simpan ke Google Sheets",
        "saving_data": "Menyimpan data...",
        "save_success": "✅ Data berhasil disimpan ke Google Sheets!",
        "view_spreadsheet": "🔗 Lihat Spreadsheet",
        "add_new_button": "➕ Tambah Data Baru",
        "upload_fail": "❌ Gagal upload: ",
        "stats_header": "📈 Statistik Trading (7 Hari Terakhir)",
        "load_stats_button": "🔄 Muat Statistik",
        "available_columns": "Kolom yang tersedia:",
        "winrate_col_error": "Tidak dapat menemukan kolom winrate. Periksa header sheet Anda.",
        "winrate_chart_title": "### Winrate 7 Hari Terakhir",
        "tpsl_chart_title": "### Perbandingan TP vs SL",
        "stats_summary_title": "### Ringkasan Statistik",
        "avg_winrate": "Rata-rata Winrate",
        "total_tp": "Total TP",
        "total_sl": "Total SL",
        "total_signals": "Total Signals",
        "overall_winrate": "Overall Winrate",
        "completion_rate": "Completion Rate",
        "recent_data_title": "### Data 7 Hari Terakhir",
        "no_data_info": "Belum ada data yang cukup untuk ditampilkan",
        "no_sheet_data": "Belum ada data yang tersimpan dalam Google Sheets",
        "stats_load_fail": "Gagal memuat statistik: ",
        "config_header": "🔧 Konfigurasi",
        "config_text": """
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
        """,
        "footer": "<div style='text-align: center'>Made with ❤️ by Lian Capital</div>",
        "language_selector": "Pilih Bahasa:",
        "ai_system_prompt": "Kamu adalah analis trading profesional yang memberikan insight tajam, profesional dan bernilai tinggi. Kamu memahami berbagai strategi trading dan metrik kinerja.",
        "ai_trading_prompt": """
        Analisis data trading berikut dan berikan komentar profesional dalam Bahasa Indonesia (maksimal 80 kata):
        
        - Tanggal: {date}
        - Total Signal: {total_signal}
        - Take-Profits: {tp}
        - Stop-Losses: {sl}
        - Finished: {finished}
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
    },
    "en": {
        "page_title": "Trading Report | Lian Capital",
        "main_title": "📊 Daily Trading Results Summary",
        "app_description": "A simple application to record and analyze your daily trading performance.",
        "input_format_info": """
        ℹ️ **Input Format:**
        ```
        📅 18 April 2025 Daily Trading Report
        
        Total Signals: 15
        Take-Profits: 10
        Stop-Losses: 3
        ```
        """,
        "input_placeholder": """📅 DD Month YYYY Daily Trading Report

Total Signals: XX
Take-Profits: XX
Stop-Losses: XX""",
        "input_label": "Copy & paste your trading recap here:",
        "process_button": "🔍 Process and Calculate",
        "clear_button": "🧹 Clear",
        "new_input_button": "🔄 New Input",
        "parsing_error": "❌ Parsing error: ",
        "format_reminder": """
        **Make sure the format follows the example:**
        ```
        📅 Date Daily Trading Report
        
        Total Signals: [Number]
        Take-Profits: [Number]
        Stop-Losses: [Number]
        ```
        """,
        "loading_ai": "Getting AI analysis...",
        "ai_error": "⚠️ Cannot use AI, using backup analysis: ",
        "results_header": "📋 Analysis Results:",
        "total_signal": "Total Signals",
        "take_profits": "Take-Profits",
        "stop_losses": "Stop-Losses",
        "date": "Date",
        "finished": "Finished",
        "winrate": "Winrate",
        "analysis_header": "💡 Trading Analysis:",
        "edit_analysis": "Edit analysis if needed:",
        "back_button": "« Back",
        "save_button": "📤 Save to Google Sheets",
        "saving_data": "Saving data...",
        "save_success": "✅ Data successfully saved to Google Sheets!",
        "view_spreadsheet": "🔗 View Spreadsheet",
        "add_new_button": "➕ Add New Data",
        "upload_fail": "❌ Upload failed: ",
        "stats_header": "📈 Trading Statistics (Last 7 Days)",
        "load_stats_button": "🔄 Load Statistics",
        "available_columns": "Available columns:",
        "winrate_col_error": "Couldn't find a column containing winrate. Check your sheet headers.",
        "winrate_chart_title": "### Winrate Last 7 Days",
        "tpsl_chart_title": "### TP vs SL Comparison",
        "stats_summary_title": "### Statistical Summary",
        "avg_winrate": "Average Winrate",
        "total_tp": "Total TP",
        "total_sl": "Total SL",
        "total_signals": "Total Signals",
        "overall_winrate": "Overall Winrate",
        "completion_rate": "Completion Rate",
        "recent_data_title": "### Last 7 Days Data",
        "no_data_info": "Not enough data to display yet",
        "no_sheet_data": "No data stored in Google Sheets yet",
        "stats_load_fail": "Failed to load statistics: ",
        "config_header": "🔧 Configuration",
        "config_text": """
        ### API Key and Google Service Account Configuration
        
        For correct configuration, add the following secrets to Streamlit Cloud:
        
        1. `OPENAI_API_KEY` - for generating AI comments
        2. `gcp_service_account` - for Google Sheets access
        
        Correct TOML format:
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
        """,
        "footer": "<div style='text-align: center'>Made with ❤️ by Lian Capital</div>",
        "language_selector": "Select Language:",
        "ai_system_prompt": "You are a professional trading analyst providing sharp, professional, and high-value insights. You understand various trading strategies and performance metrics.",
        "ai_trading_prompt": """
        Analyze the following trading data and provide a professional comment in English (maximum 80 words):
        
        - Date: {date}
        - Total Signals: {total_signal}
        - Take-Profits: {tp}
        - Stop-Losses: {sl}
        - Finished: {finished}
        - Winrate: {winrate}%
        - Completion Rate: {completion_rate:.1f}%
        
        Provide a sharp analysis that helps traders by considering:
        1. Quality of trading performance (whether the winrate is good or needs improvement)
        2. Evaluation of TP/SL ratio and its significance
        3. Signal completion rate and its implications
        4. Concrete suggestions to improve trading performance for the next day
        5. If winrate is below 50%, provide positive motivation
        
        Comment must be objective, concise, and straight to the point.
        """
    }
}

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
def get_ai_trading_comment(data, language="id"):
    client = get_openai_client()
    if not client:
        return "AI analisis tidak tersedia (API key tidak dikonfigurasi)"
    
    # Siapkan prompt untuk AI dengan data trading
    winrate = data["Winrate_pct"]
    tp = data["TP"]
    sl = data["SL"]
    completion_rate = (data["Finished"] / data["Total_Signal"] * 100) if data["Total_Signal"] > 0 else 0
    
    # Get the prompt in the selected language
    prompt = LANGUAGES[language]["ai_trading_prompt"].format(
        date=data['Date'],
        total_signal=data['Total_Signal'],
        tp=tp,
        sl=sl,
        finished=data['Finished'],
        winrate=winrate,
        completion_rate=completion_rate
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo", # atau "gpt-4" untuk hasil lebih baik
            messages=[
                {"role": "system", "content": LANGUAGES[language]["ai_system_prompt"]},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error saat menghubungi AI: {str(e)}")
        return generate_backup_comment(data, language)  # Gunakan backup comment jika AI gagal

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
def generate_backup_comment(data, language="id"):
    """Menghasilkan komentar otomatis jika OpenAI API tidak tersedia."""
    winrate = data["Winrate_pct"]
    tp = data["TP"]
    sl = data["SL"]
    total = data["Total_Signal"]
    finished = data["Finished"]
    
    if language == "id":
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
    else:  # English version
        # Winrate analysis
        if winrate >= 80:
            performance = "Excellent performance with high winrate"
        elif winrate >= 70:
            performance = "Good performance with solid winrate"
        elif winrate >= 60:
            performance = "Decent performance, still above market average"
        elif winrate >= 50:
            performance = "Average performance, needs improvement"
        else:
            performance = "Below-average performance, strategy evaluation required"
        
        # Completion ratio analysis
        completion_rate = (finished / total) * 100 if total > 0 else 0
        if completion_rate >= 90:
            completion = "Signal execution rate is excellent"
        elif completion_rate >= 70:
            completion = "Signal execution rate is decent"
        else:
            completion = "Need to improve signal execution rate"
        
        # TP:SL ratio analysis
        if tp > sl and tp > 0:
            ratio = f"Positive TP:SL ratio of {tp}:{sl} indicates effective strategy"
        elif tp == sl and tp > 0:
            ratio = f"Balanced TP:SL ratio of {tp}:{sl}, needs improvement"
        elif tp > 0 and sl > 0:
            ratio = f"Negative TP:SL ratio of {tp}:{sl}, strategy adjustment needed"
        else:
            ratio = "Not enough data for TP:SL ratio analysis"
        
        # Recommendations
        if winrate >= 60:
            recommendation = "Maintain strategy and gradually increase trading volume."
        elif winrate >= 50:
            recommendation = "Evaluate suboptimal trading setups, focus on signal quality."
        else:
            recommendation = "Revise entry/exit strategy and recalibrate risk management parameters."
    
    # Gabungkan komentar
    comment = f"{performance}. {completion}. {ratio}. Rekomendasi: {recommendation}"
    return comment

# -------- UI STREAMLIT --------
# Initialize session state for language preference
if 'language' not in st.session_state:
    st.session_state.language = "id"  # Default to Indonesian

# Make sure all other session states are initialized
if 'result' not in st.session_state:
    st.session_state.result = None
if 'upload_success' not in st.session_state:
    st.session_state.upload_success = False
if 'ai_comment_loading' not in st.session_state:
    st.session_state.ai_comment_loading = False

# Get current language text dictionary
lang = LANGUAGES[st.session_state.language]

st.set_page_config(
    page_title=lang["page_title"],
    page_icon="📊",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Language selector in sidebar
with st.sidebar:
    selected_lang = st.selectbox(
        lang["language_selector"],
        options=["id", "en"],
        format_func=lambda x: "Bahasa Indonesia" if x == "id" else "English",
        index=0 if st.session_state.language == "id" else 1
    )
    
    # Update language if changed
    if selected_lang != st.session_state.language:
        st.session_state.language = selected_lang
        # Update the lang variable
        lang = LANGUAGES[st.session_state.language]
        st.experimental_rerun()

st.title(lang["main_title"])
st.markdown(lang["app_description"])

# Reset button (header)
if st.session_state.result and not st.session_state.ai_comment_loading:
    if st.button(lang["new_input_button"], key="reset_top"):
        st.session_state.result = None
        st.session_state.upload_success = False
        st.experimental_rerun()

# Contoh pesan untuk panduan format
if not st.session_state.result:
    st.info(lang["input_format_info"])

# Area input teks
if not st.session_state.result:
    input_text = st.text_area(
        lang["input_label"],
        placeholder=lang["input_placeholder"],
        height=200
    )
    
    col1, col2 = st.columns([1, 1])
    with col1:
        process_button = st.button(lang["process_button"], use_container_width=True)
    with col2:
        clear_button = st.button(lang["clear_button"], use_container_width=True)
        if clear_button:
            st.experimental_rerun()

    # Proses parsing otomatis
    if process_button and input_text:
        try:
            result = parse_trading_summary(input_text)
            st.session_state.result = result
            
            # Set flag untuk loading AI comment
            st.session_state.ai_comment_loading = True
            st.experimental_rerun()
            
        except Exception as e:
            st.error(f"{lang['parsing_error']}{str(e)}")
            st.markdown(lang["format_reminder"])

# Proses loading AI comment jika diperlukan
if st.session_state.ai_comment_loading and st.session_state.result:
    with st.spinner(lang["loading_ai"]):
        try:
            ai_comment = get_ai_trading_comment(st.session_state.result, st.session_state.language)
            st.session_state.result["Comment"] = ai_comment
        except Exception as e:
            st.warning(f"{lang['ai_error']}{str(e)}")
            backup_comment = generate_backup_comment(st.session_state.result, st.session_state.language)
            st.session_state.result["Comment"] = backup_comment
        
        st.session_state.ai_comment_loading = False
        st.experimental_rerun()

# Tampilkan hasil
if st.session_state.result and not st.session_state.ai_comment_loading:
    st.markdown("---")
    st.subheader(lang["results_header"])
    
    # Buat kartu metrik dengan gaya yang lebih baik
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(lang["total_signal"], st.session_state.result["Total_Signal"])
    with col2:
        st.metric(lang["take_profits"], st.session_state.result["TP"])
    with col3:
        st.metric(lang["stop_losses"], st.session_state.result["SL"])
    
    col4, col5, col6 = st.columns(3)
    with col4:
        st.metric(lang["date"], st.session_state.result["Date"])
    with col5:
        st.metric(lang["finished"], st.session_state.result["Finished"])
    with col6:
        # Use the correct winrate label
        winrate = st.session_state.result["Winrate_pct"]
        
        # Tampilkan winrate dengan warna berdasarkan nilai
        if winrate >= 70:
            st.markdown(f"<h3 style='color:#36B37E'>{lang['winrate']}: {winrate}%</h3>", unsafe_allow_html=True)
        elif winrate < 50:
            st.markdown(f"<h3 style='color:#FF5630'>{lang['winrate']}: {winrate}%</h3>", unsafe_allow_html=True)
        else:
            st.markdown(f"<h3>{lang['winrate']}: {winrate}%</h3>", unsafe_allow_html=True)

    # Tampilkan komentar AI
    st.subheader(lang["analysis_header"])
    st.info(st.session_state.result.get("Comment", ""))
    
    # Edit komentar AI jika perlu
    edited_comment = st.text_area(
        lang["edit_analysis"],
        value=st.session_state.result.get("Comment", ""),
        height=100
    )
    st.session_state.result["Comment"] = edited_comment

    # Tombol upload final
    col_back, col_upload = st.columns([1, 2])
    
    with col_back:
        if st.button(lang["back_button"], use_container_width=True):
            st.session_state.result = None
            st.experimental_rerun()
    
    with col_upload:
        upload_btn = st.button(lang["save_button"], key="upload_final", use_container_width=True)
    
    if upload_btn:
        try:
            with st.spinner(lang["saving_data"]):
                sheet = connect_to_gsheet()
                
                # Format tanggal yang lebih konsisten untuk keperluan analisis
                date_str = st.session_state.result["Date"]
                
                # Simpan data ke Google Sheets
                sheet.append_row([
                    date_str,  # Simpan tanggal asli
                    st.session_state.result["Total_Signal"],
                    st.session_state.result["Finished"],
                    st.session_state.result["TP"],
                    st.session_state.result["SL"],
                    f"{st.session_state.result['Winrate_pct']}%",
                    st.session_state.result["Comment"]
                ])
            st.success(lang["save_success"])
            st.balloons()
            
            # Tampilkan link ke spreadsheet
            st.markdown(f"[{lang['view_spreadsheet']}](https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID})")
            
            # Reset status dan tampilkan tombol untuk data baru
            st.session_state.upload_success = True
            
            if st.button(lang["add_new_button"], key="add_new"):
                st.session_state.result = None
                st.session_state.upload_success = False
                st.experimental_rerun()
                
        except Exception as e:
            st.error(f"{lang['upload_fail']}{str(e)}")

with st.expander(lang["stats_header"]):
    if st.button(lang["load_stats_button"]):
        try:
            import pandas as pd
            import altair as alt
            
            sheet = connect_to_gsheet()
            
            # Get all data
            data = sheet.get_all_records()
            
            if data:
                df = pd.DataFrame(data)
                
                # First check what columns are actually available
                st.write(f"{lang['available_columns']} {df.columns.tolist()}")
                
                # Find the winrate column (adapt to whatever name is actually in your sheet)
                winrate_col = None
                for col in df.columns:
                    if 'winrate' in col.lower() or 'win rate' in col.lower() or 'win_rate' in col.lower():
                        winrate_col = col
                        break
                
                if not winrate_col:
                    st.error(lang["winrate_col_error"])
                else:
                    # Convert all numeric columns to proper numeric types
                    numeric_columns = ['Total_Signal', 'Finished', 'TP', 'SL']
                    for col in numeric_columns:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                    
                    # Convert winrate from string to numeric (handling % symbol if present)
                    # Handle empty strings and convert to numeric safely
                    df['Winrate_num'] = pd.to_numeric(
                        df[winrate_col].astype(str).str.rstrip('%').replace('', '0'), 
                        errors='coerce'
                    ).fillna(0)
                    
                    # Filter out rows that have no data (all zeros or empty values)
                    # Identify numeric columns to check for zeros
                    data_columns = ['Total_Signal', 'TP', 'SL']
                    valid_columns = [col for col in data_columns if col in df.columns]
                    
                    # Add a new column to check if row has actual data (not all zeros)
                    if valid_columns:
                        df['has_data'] = df[valid_columns].sum(axis=1) > 0
                        # Filter to only rows that have data
                        df_filtered = df[df['has_data']]
                    else:
                        df_filtered = df
                    
                    # Tunjukkan hanya 7 data terakhir yang memiliki data
                    df_recent = df_filtered.tail(7)
                    
                    # PERBAIKAN: Tambahkan kolom Date_display untuk chart
                    # Gunakan kolom Date yang ada sebagai dasar untuk Date_display
                    if 'Date' in df_recent.columns:
                        df_recent['Date_display'] = df_recent['Date']
                    
                    # Buat chart dengan Altair
                    if len(df_recent) > 0:
                        # Winrate Chart
                        st.write(lang["winrate_chart_title"])
                        chart_winrate = alt.Chart(df_recent).mark_line(point=True).encode(
                            x=alt.X('Date_display:N', title=lang["date"], sort=None),
                            y=alt.Y('Winrate_num:Q', title=lang["winrate"] + ' (%)', scale=alt.Scale(domain=[0, 100])),
                            tooltip=['Date_display', winrate_col, 'Total_Signal', 'TP', 'SL']
                        ).properties(height=250)
                        st.altair_chart(chart_winrate, use_container_width=True)
                        
                        # TP/SL Chart
                        st.write(lang["tpsl_chart_title"])
                        df_melted = pd.melt(df_recent, id_vars=['Date_display'], value_vars=['TP', 'SL'], 
                                          var_name='Type', value_name='Count')
                        
                        chart_tpsl = alt.Chart(df_melted).mark_bar().encode(
                            x=alt.X('Date_display:N', title=lang["date"]),
                            y=alt.Y('Count:Q', title='Count'),
                            color=alt.Color('Type:N', scale=alt.Scale(
                                domain=['TP', 'SL'],
                                range=['#36b37e', '#ff5630']
                            )),
                            tooltip=['Date_display', 'Type', 'Count']
                        ).properties(height=250)
                        st.altair_chart(chart_tpsl, use_container_width=True)
                        
                        # Ringkasan statistik
                        st.write(lang["stats_summary_title"])
                        avg_winrate = df_recent['Winrate_num'].mean()
                        total_tp = df_recent['TP'].sum()
                        total_sl = df_recent['SL'].sum() 
                        total_signals = df_recent['Total_Signal'].sum()
                        
                        col1, col2, col3 = st.columns(3)
                        col1.metric(lang["avg_winrate"], f"{avg_winrate:.1f}%")
                        col2.metric(lang["total_tp"], int(total_tp))
                        col3.metric(lang["total_sl"], int(total_sl))
                        
                        # Baris kedua
                        col4, col5, col6 = st.columns(3)
                        col4.metric(lang["total_signals"], int(total_signals))
                        
                        if total_tp + total_sl > 0:
                            overall_winrate = (total_tp / (total_tp + total_sl)) * 100
                            col5.metric(lang["overall_winrate"], f"{overall_winrate:.1f}%")
                        
                        completion_rate = ((total_tp + total_sl) / total_signals) * 100 if total_signals > 0 else 0
                        col6.metric(lang["completion_rate"], f"{completion_rate:.1f}%")
                        
                        # Data lengkap
                        st.write(lang["recent_data_title"])
                        # Make sure we use the actual column names from the dataframe
                        if 'Date_display' in df_recent.columns:
                            display_df = df_recent.copy()
                            # Use Date_display for display purposes but keep original columns for reference
                            display_columns = ['Date_display', 'Total_Signal', 'TP', 'SL', winrate_col]
                            # Check if all columns exist in the dataframe before displaying
                            valid_columns = [col for col in display_columns if col in display_df.columns]
                            st.dataframe(display_df[valid_columns], use_container_width=True)
                        else:
                            # Fallback to original data if Date_display is not available
                            display_columns = ['Date', 'Total_Signal', 'TP', 'SL', winrate_col]
                            valid_columns = [col for col in display_columns if col in df_recent.columns]
                            st.dataframe(df_recent[valid_columns], use_container_width=True)
                    else:
                        st.info(lang["no_data_info"])
            else:
                st.info(lang["no_sheet_data"])
        except Exception as e:
            st.error(f"{lang['stats_load_fail']}{str(e)}")

# Tambahkan petunjuk konfigurasi
with st.expander(lang["config_header"]):
    st.markdown(lang["config_text"])

st.markdown("---")
st.markdown(lang["footer"], unsafe_allow_html=True)
