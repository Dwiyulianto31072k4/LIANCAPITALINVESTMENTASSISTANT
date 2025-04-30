import streamlit as st
import pandas as pd
import gspread
from google.oauth2 import service_account
import requests
import json
from datetime import datetime
import re

# Konfigurasi halaman Streamlit
st.set_page_config(page_title="Trading Data Processor", layout="wide")
st.title("Aplikasi Input Data Trading dengan DeepSeek R1 AI")

# Fungsi untuk koneksi ke Google Sheets
@st.cache_resource
def connect_to_gsheets():
    # Buat kredensial dari secrets
    credentials = service_account.Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    
    # Buat klien gspread
    client = gspread.authorize(credentials)
    
    return client

# Fungsi untuk menginisialisasi DeepSeek R1 API Client
def generate_ai_comment(data_dict):
    DEEPSEEK_API_KEY = st.secrets["deepseek_api_key"]
    DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
    
    # Membuat prompt untuk AI
    prompt = f"""
    Analisis data trading berikut dan berikan komentar singkat (maksimal 1-2 kalimat) dalam Bahasa Indonesia:
    
    Periode: {data_dict['date']}
    Total Signal: {data_dict['total_signal']}
    Finished: {data_dict['finished']}
    Take Profit (TP): {data_dict['tp']}
    Stop Loss (SL): {data_dict['sl']}
    Win Rate: {data_dict['winrate_pct']}%
    
    Target 1 hits: {data_dict['target1_count']} ({', '.join(data_dict['target1'])})
    Target 2 hits: {data_dict['target2_count']} ({', '.join(data_dict['target2'])})
    Target 3 hits: {data_dict['target3_count']} ({', '.join(data_dict['target3'])})
    Target 4 hits: {data_dict['target4_count']} ({', '.join(data_dict['target4'])})
    Running: {data_dict['running_count']} ({', '.join(data_dict['running'])})
    Stop Loss hits: {data_dict['sl_count']} ({', '.join(data_dict['sl_tokens'])})
    
    Berikan penilaian tentang performa trading, highlight token/coin terbaik, dan saran singkat untuk monitoring.
    """
    
    # Data untuk request ke DeepSeek API
    data = {
        "model": "deepseek-r1-chat",  # Model DeepSeek R1
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 300
    }
    
    # Headers untuk request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
    }
    
    # Melakukan request ke DeepSeek API
    try:
        response = requests.post(DEEPSEEK_API_URL, headers=headers, json=data)
        response_data = response.json()
        
        # Ekstrak komentar dari respons
        if "choices" in response_data and len(response_data["choices"]) > 0:
            comment = response_data["choices"][0]["message"]["content"].strip()
            return comment
        else:
            return "Tidak dapat menghasilkan komentar. Periksa respons API."
    except Exception as e:
        return f"Error saat menggunakan DeepSeek API: {str(e)}"

# Fungsi untuk mengekstrak data dari input teks
def extract_data(text):
    # Temukan tanggal
    date_match = re.search(r'(\d{2}/\d{2})-(\d{2}/\d{2})', text)
    if date_match:
        end_date = date_match.group(2)  # Mengambil tanggal akhir
        month, day = end_date.split('/')
        year = datetime.now().year
        date_formatted = f"{year}-{month}-{day}"
    else:
        date_formatted = datetime.now().strftime("%Y-%m-%d")
    
    # Ekstrak total sinyal, TP, dan SL
    total_signal_match = re.search(r'Total Signals:\s*(\d+)', text)
    tp_match = re.search(r'Hitted Take-Profits:\s*(\d+)', text)
    sl_match = re.search(r'Hitted Stop-Losses:\s*(\d+)', text)
    
    total_signal = int(total_signal_match.group(1)) if total_signal_match else 0
    tp = int(tp_match.group(1)) if tp_match else 0
    sl = int(sl_match.group(1)) if sl_match else 0
    
    # Hitung finished dan winrate
    finished = tp + sl
    winrate_pct = round((tp / finished) * 100, 2) if finished > 0 else 0
    
    # Ekstrak token untuk setiap target
    def extract_tokens(pattern, text):
        match = re.search(pattern, text)
        if match:
            tokens_str = match.group(1)
            tokens = [token.strip() for token in re.split(r',\s*', tokens_str)]
            return tokens
        return []
    
    target1 = extract_tokens(r'Hitted target 1:(.*?)—{3,}', text)
    target2 = extract_tokens(r'Hitted target 2:(.*?)—{3,}', text)
    target3 = extract_tokens(r'Hitted target 3:(.*?)—{3,}', text)
    target4 = extract_tokens(r'Hitted target 4:(.*?)—{3,}', text)
    running = extract_tokens(r'Running:(.*?)—{3,}', text)
    sl_tokens = extract_tokens(r'Hitted stop loss:(.*?)—{3,}', text)
    
    # Kumpulkan semua data
    data_dict = {
        'date': date_formatted,
        'total_signal': total_signal,
        'finished': finished,
        'tp': tp,
        'sl': sl,
        'winrate_pct': winrate_pct,
        'target1': target1,
        'target1_count': len(target1),
        'target2': target2,
        'target2_count': len(target2),
        'target3': target3,
        'target3_count': len(target3),
        'target4': target4,
        'target4_count': len(target4),
        'running': running,
        'running_count': len(running),
        'sl_tokens': sl_tokens,
        'sl_count': len(sl_tokens)
    }
    
    return data_dict

# Fungsi untuk menulis data ke Google Sheets
def write_to_gsheets(client, data_dict, spreadsheet_id, worksheet_name):
    try:
        # Buka spreadsheet dan worksheet
        spreadsheet = client.open_by_key(spreadsheet_id)
        worksheet = spreadsheet.worksheet(worksheet_name)
        
        # Siapkan data untuk ditambahkan
        row = [
            data_dict['date'],
            data_dict['total_signal'],
            data_dict['finished'],
            data_dict['tp'],
            data_dict['sl'],
            data_dict['winrate_pct'],
            data_dict['comment']
        ]
        
        # Tambahkan baris baru
        worksheet.append_row(row)
        return True
    except Exception as e:
        st.error(f"Error saat menulis ke Google Sheets: {str(e)}")
        return False

# UI Aplikasi
st.header("Input Data Trading")

# Input kolom untuk Spreadsheet ID dan nama worksheet
with st.expander("Konfigurasi Spreadsheet", expanded=False):
    spreadsheet_id = st.text_input("Google Spreadsheet ID", help="ID dari Google Spreadsheet Anda")
    worksheet_name = st.text_input("Nama Worksheet", value="Table1", help="Nama worksheet di spreadsheet")

# Input area untuk data trading
st.subheader("Data Trading")
trading_input = st.text_area(
    "Masukkan data trading harian",
    height=300,
    help="Tempel data trading harian dengan format yang sama seperti contoh"
)

# Contoh input
with st.expander("Lihat Contoh Input", expanded=False):
    st.code("""04/28-04/29 Daily Results 每日結算統計 Hitted target 1: ACX, RIF, SWARMS, BIO, ZK, MAV, HIVE, MBOX, BANK, BNT, JTO, PROMPT, 1000FLOKI, ETC, API3, POWR——————————————————— Hitted target 2: COS, ALICE, ONE, CHESS, ZRX, REZ, EPIC, IOTX, BCH, B3, AIXBT, CKB, EOS, AXL, XVS, G, KMNO, SOLV, VOXEL, FHE——————————————————— Hitted target 3: GOAT,HOOK,XVG,COOKIE,VVV,MEMEFI,BR,PAXG,HIGH,PIPPIN,VIRTUAL,1INCH,DRIFT,BAN——————————————————— Hitted target 4: TOKEN, AKT, CELO, SONIC, DIA, SAFE——————————————————— Running: BAT, ETH, GLM, ALCH, SIREN, ANIME, AI16Z, AI——————————————————— Hitted stop loss: CFX, 1000000MOG, METIS, NMR, SPX, MOVE, NEIROETH, DYDX, GPS, ALPACA, 1000XEC, TRU———————————————————Total Signals: 76Hitted Take-Profits: 56Hitted Stop-Losses: 12""")

# Tombol untuk memproses data
if st.button("Proses dan Simpan Data"):
    if not trading_input:
        st.error("Data trading harian tidak boleh kosong!")
    elif not spreadsheet_id:
        st.error("Google Spreadsheet ID tidak boleh kosong!")
    else:
        with st.spinner("Memproses data..."):
            # Ekstrak data
            data_dict = extract_data(trading_input)
            
            # Tampilkan preview data yang diekstrak
            st.subheader("Preview Data")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Signal", data_dict['total_signal'])
            col2.metric("Take Profit", data_dict['tp'])
            col3.metric("Stop Loss", data_dict['sl'])
            
            col1, col2 = st.columns(2)
            col1.metric("Finished", data_dict['finished'])
            col2.metric("Win Rate", f"{data_dict['winrate_pct']}%")
            
            # Generate komentar AI
            with st.spinner("Menghasilkan komentar dengan DeepSeek R1..."):
                comment = generate_ai_comment(data_dict)
                data_dict['comment'] = comment
                
                st.subheader("Komentar AI")
                st.write(comment)
            
            # Simpan ke Google Sheets
            with st.spinner("Menyimpan ke Google Sheets..."):
                client = connect_to_gsheets()
                success = write_to_gsheets(client, data_dict, spreadsheet_id, worksheet_name)
                
                if success:
                    st.success("Data berhasil disimpan ke Google Sheets!")
                else:
                    st.error("Gagal menyimpan data. Periksa kembali konfigurasi spreadsheet.")

# Tampilkan informasi penggunaan
st.divider()
st.caption("""
**Cara Penggunaan:**
1. Masukkan Google Spreadsheet ID dan nama worksheet
2. Tempel data trading harian di area input
3. Klik tombol "Proses dan Simpan Data"
4. Aplikasi akan mengekstrak data, menghasilkan komentar dengan DeepSeek R1, dan menyimpan ke spreadsheet
""")
